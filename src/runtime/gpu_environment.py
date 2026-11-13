"""Side-effect-free CUDA policy. Device assignment belongs to the caller/scheduler."""
import os


def visibility_snapshot(env=None):
    env = os.environ if env is None else env
    return dict(present='CUDA_VISIBLE_DEVICES' in env,
                value=env.get('CUDA_VISIBLE_DEVICES'))


def require_gpu_assignment(env=None):
    """Reject explicit disable/malformed assignment, never expand or rewrite it."""
    snap = visibility_snapshot(env)
    value = snap['value']
    if value is not None:
        parts = value.split(',')
        if not value.strip() or any(not p.strip() or p.strip() in ('-1', 'NoDevFiles', 'none', 'void') for p in parts):
            raise RuntimeError('GPU explicitly disabled or invalid CUDA_VISIBLE_DEVICES')
        if any(p != p.strip() for p in parts):
            raise RuntimeError('Ambiguous whitespace in CUDA_VISIBLE_DEVICES')
        if len(set(parts)) != len(parts):
            raise RuntimeError('Duplicate CUDA device assignment')
    return snap


def configure_determinism(env=None):
    """Call explicitly before importing torch. CUDA visibility is untouched."""
    env = os.environ if env is None else env
    existing = env.get('CUBLAS_WORKSPACE_CONFIG')
    if existing not in (None, ':4096:8'):
        raise RuntimeError('Conflicting CuBLAS deterministic configuration')
    env['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    return require_gpu_assignment(env)


def assert_visibility(expected, env=None):
    if visibility_snapshot(env) != expected:
        raise RuntimeError('CUDA visibility changed during module imports')


def require_cuda(torch_module, expected):
    assert_visibility(expected)
    require_gpu_assignment()
    if not torch_module.cuda.is_available():
        raise RuntimeError('CUDA unavailable under inherited assignment; no training launched')
    return dict(visibility=expected, torch=torch_module.__version__,
                CUDA=torch_module.version.cuda, visible_devices=torch_module.cuda.device_count(),
                selected_logical_device=0, GPU=torch_module.cuda.get_device_name(0),
                total_bytes=torch_module.cuda.get_device_properties(0).total_memory)
