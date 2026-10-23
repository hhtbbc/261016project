"""Independent Direct training contracts and checkpointing; SI evaluation stays separate."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[2]
LABEL = 'INDEPENDENT_IMPLEMENTATION / SYNTHETIC_ENGINEERING_ONLY'


def local_path(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    path.resolve().relative_to(ROOT)
    return path


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False


def build_direct(architecture):
    """Instantiate unchanged official AFNONet from random initialization, no weights read."""
    import sys
    sys.path.insert(0, str(ROOT / 'third_party/FourCastDEN_linux'))
    from models.afnonet import AFNONet
    return AFNONet(**architecture)


def utc(value):
    value = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError('Explicit UTC timezone required')
    return value.astimezone(timezone.utc)


class AffineNormalizer:
    """174 native-cgs channels including LBC; statistics must be separately provenance-checked."""
    def __init__(self, means, stds):
        self.means = np.asarray(means, dtype=np.float64)
        self.stds = np.asarray(stds, dtype=np.float64)
        if self.means.shape != (174, 1, 1) or self.stds.shape != self.means.shape:
            raise ValueError('174 per-layer statistics required')
        if not np.isfinite(self.means).all() or not np.isfinite(self.stds).all() or (self.stds <= 0).any():
            raise ValueError('Invalid statistics')

    def encode(self, native):
        native = np.asarray(native)
        if native.shape != (174, 36, 72) or not np.isfinite(native).all():
            raise ValueError('Invalid native fields')
        return ((native - self.means) / self.stds).astype(np.float32)

    def decode(self, encoded):
        return np.asarray(encoded, dtype=np.float64) * self.stds + self.means


class OfficialFrameSource:
    """Adapter for an already configured author TGCMDataset; no new time/solar formulas."""
    def __init__(self, dataset):
        self.dataset = dataset
        self.indices = {t.replace(tzinfo=timezone.utc): i for i, t in enumerate(dataset.epochs)}
        if len(self.indices) != len(dataset.epochs):
            raise ValueError('Duplicate source times')

    def __call__(self, epoch):
        data, sw, *_ = self.dataset.get_data([self.indices[utc(epoch)]], inference=True)
        frame = torch.as_tensor(data[0], dtype=torch.float32)
        scalar = torch.as_tensor(sw[0], dtype=torch.float32).reshape(4)
        if frame.shape != (177, 36, 72) or not torch.isfinite(frame).all() or not torch.isfinite(scalar).all():
            raise ValueError('Invalid official encoded frame')
        return frame[:171], frame[171:], scalar


class EpochPairs(torch.utils.data.Dataset):
    """Single-hour Direct pairs; future physical state appears only as the target."""
    def __init__(self, epochs, source, split):
        if split not in ('train', 'validation'):
            raise ValueError('Explicit train or validation split required')
        self.epochs = [utc(x) for x in epochs]
        self.source, self.split = source, split
        years = set(range(2000, 2022)) if split == 'train' else {2022}
        if len(self.epochs) < 2 or any(x.year not in years for x in self.epochs):
            raise ValueError('Only 2000-2021 train / 2022 validation allowed; 2023 is test-only')
        if any(b - a != timedelta(hours=1) or b.year != a.year for a, b in zip(self.epochs, self.epochs[1:])):
            raise ValueError('Noncontiguous or cross-year window')

    def __len__(self):
        return len(self.epochs) - 1

    def __getitem__(self, i):
        if i < 0 or i >= len(self):
            raise IndexError(i)
        current, _, _ = self.source(self.epochs[i])
        target, aux, scalar = self.source(self.epochs[i + 1])
        x = torch.cat((current, aux), dim=0)
        y = torch.as_tensor(target)
        s = torch.as_tensor(scalar).reshape(1, 4)
        if x.shape != (177, 36, 72) or y.shape != (171, 36, 72) or not all(torch.isfinite(t).all() for t in (x, y, s)):
            raise ValueError('Malformed pair')
        return x, s, y


def validate_disjoint(train, validation):
    if train.split != 'train' or validation.split != 'validation' or set(train.epochs) & set(validation.epochs):
        raise ValueError('Overlapping or incorrect splits')


def synthetic_batch(seed, device='cpu'):
    generator = torch.Generator(device='cpu').manual_seed(seed)
    x = torch.randn((1, 177, 36, 72), generator=generator) * .1
    s = torch.randn((1, 1, 4), generator=generator) * .1
    # Arbitrary synthetic mapping, not physical atmosphere or a reference density field.
    target = .5 * x[:, :171] + .01 * s[:, :, :1].reshape(1, 1, 1, 1)
    return tuple(t.to(device) for t in (x, s, target))


class DirectTrainer:
    def __init__(self, model, config):
        self.model, self.config, self.step = model, config, 0
        opt = config['optimizer']
        if opt['name'] == 'SGD':
            self.optimizer = torch.optim.SGD(model.parameters(), lr=opt['lr'], momentum=opt['momentum'])
        elif opt['name'] == 'AdamW':
            self.optimizer = torch.optim.AdamW(model.parameters(), lr=opt['lr'], weight_decay=opt['weight_decay'])
        else:
            raise ValueError('Unsupported explicit optimizer')
        schedule = config['scheduler']
        self.scheduler = torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=schedule['step_size'], gamma=schedule['gamma'])

    def loss(self, batch):
        x, s, target = batch
        if x.shape[1:] != (177, 36, 72) or s.shape[1:] != (1, 4) or target.shape[1:] != (171, 36, 72):
            raise ValueError('Batch shape mismatch')
        if x.shape[0] != s.shape[0] or x.shape[0] != target.shape[0] or not all(torch.isfinite(t).all() for t in batch):
            raise ValueError('Invalid batch')
        prediction = self.model(x, s)
        if prediction.shape != target.shape or not torch.isfinite(prediction).all():
            raise ValueError('Invalid model output')
        loss = nn.functional.mse_loss(prediction, target)
        if not torch.isfinite(loss):
            raise ValueError('Nonfinite loss')
        return loss

    def train_step(self, batch):
        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)
        loss = self.loss(batch)
        loss.backward()
        gradients = [p.grad for p in self.model.parameters() if p.grad is not None]
        if not gradients or not all(torch.isfinite(g).all() for g in gradients):
            raise ValueError('Nonfinite or absent gradient')
        norm = torch.sqrt(sum(g.detach().double().square().sum() for g in gradients)).item()
        if norm <= 0:
            raise ValueError('Zero gradient')
        clip = self.config['gradient_clip_norm']
        if clip is not None:
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), clip, error_if_nonfinite=True)
        self.optimizer.step()
        self.scheduler.step()
        self.step += 1
        return dict(step=self.step, loss=loss.item(), gradient_l2_before_clip=norm,
                    unused_parameters=[n for n, p in self.model.named_parameters() if p.grad is None])

    def validation_step(self, batch):
        training = self.model.training
        self.model.eval()
        try:
            with torch.no_grad():
                return self.loss(batch).item()
        finally:
            self.model.train(training)

    def save(self, path, metadata):
        path = local_path(path)
        rng = dict(python=random.getstate(), numpy=np.random.get_state(), torch=torch.get_rng_state(),
                   cuda=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [])
        payload = dict(model_state=self.model.state_dict(), optimizer_state=self.optimizer.state_dict(),
                       scheduler_state=self.scheduler.state_dict(), step=self.step, rng=rng,
                       config=self.config, metadata=metadata, model_training=self.model.training)
        with path.open('xb') as f:
            torch.save(payload, f)

    def restore(self, path, *, trusted_local=False):
        if not trusted_local:
            raise ValueError('Only trusted locally generated training checkpoints may be loaded')
        path = local_path(path)
        if path.resolve().is_relative_to(ROOT / 'models') or path.suffix != '.pt':
            raise ValueError('Official checkpoints are not training resume sources')
        p = torch.load(path, map_location=next(self.model.parameters()).device, weights_only=False)
        if p['config'] != self.config or p['metadata'].get('label') != LABEL:
            raise ValueError('Checkpoint contract mismatch')
        self.model.load_state_dict(p['model_state'], strict=True)
        self.optimizer.load_state_dict(p['optimizer_state'])
        self.scheduler.load_state_dict(p['scheduler_state'])
        self.step = p['step']
        random.setstate(p['rng']['python']);np.random.set_state(p['rng']['numpy'])
        torch.set_rng_state(p['rng']['torch'].cpu())
        if p['rng']['cuda']:
            torch.cuda.set_rng_state_all([x.cpu() for x in p['rng']['cuda']])
        self.model.train(p['model_training'])
        return p['metadata']
