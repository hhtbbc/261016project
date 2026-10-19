# FourCastDEN: 2023 Inference Package

## Overview

FourCastDEN is an Adaptive Fourier Neural Operator (AFNO)-based framework for forecasting the thermospheric state. The model predicts neutral temperature, winds, geopotential height, and neutral mass density from the current thermospheric state, lower-boundary conditions, solar forcing, geomagnetic forcing, and solar-geophysical indices.

This package is intended **only for inference on the 2023 test dataset**. It does not include training code, training data, validation data, or instructions for retraining the models.

The following files are distributed separately from the source-code archive:

- four trained PyTorch checkpoint files;
- the processed 2023 hourly test dataset;
- the standard static-data directory;
- the static-data directory calculated after applying `log10` to `DEN`.

## Supported pretrained models

The four checkpoints must be used with the configuration that was used during training. Replace the example checkpoint names below with the actual supplied filenames.

| Model | Example checkpoint             | `flow` | `n_history` | `log_DEN` | Static data |
|---|--------------------------------|---:|---:|---:|---|
| Direct | `Direct_ckpt.tar`              | `False` | `0` | `False` | `static` |
| Flow | `Flow_ckpt.tar`                | `True` | `0` | `False` | `static` |
| 1-hour history | `Baseline_1h_history_ckpt.tar` | `False` | `1` | `False` | `static` |
| log-DEN | `Baseline_log_DEN_ckpt.tar`    | `False` | `0` | `True` | `static_log` |

`n_history: 0` uses only the state at the forecast initialization time. `n_history: 1` additionally uses the previous one-hour state. The history setting changes the number of model input channels, so a checkpoint must not be used with the wrong `n_history` value.

The Flow model predicts increments and adds them to the preceding state. The other three models use direct-state prediction.

## Recommended directory layout

After extracting the source archive and adding the separately supplied files, the project can be arranged as follows:

```text
FourCastDEN/
├── config/
│   ├── AFNO.yaml
│   └── environment.yaml
├── dataset/
├── inference/
├── models/
├── utils/
├── eval_tiegcm.py
├── inference.sh
├── checkpoints/
│   ├── Direct_ckpt.tar
│   ├── Flow_ckpt.tar
│   ├── Baseline_1h_history_ckpt.tar
│   └── Baseline_log_DEN_ckpt.tar
├── test/
│   └── 2023/
│       ├── 2023_01_01_000000.npz
│       ├── 2023_01_01_010000.npz
│       └── ...
├── static/
│   ├── global_means.npz
│   ├── global_stds.npz
│   ├── time_means.npz
│   ├── lat.npy
│   ├── lon.npy
│   ├── lev.npy
│   ├── ilev.npy
│   └── mag.npz
└── static_log/
    ├── global_means.npz
    ├── global_stds.npz
    ├── time_means.npz
    ├── lat.npy
    ├── lon.npy
    ├── lev.npy
    ├── ilev.npy
    └── mag.npz
```

The `.npz` files must be located directly inside the directory assigned to `test_data_path`. For the layout above, use `./test/2023`, not `./test`.

The 2023 files must already be in the processed hourly `.npz` format expected by `dataset/dataset_tiegcm.py`. No training-data preparation is required for this inference-only package.

## Environment setup

Create the supplied Conda environment from the project root:

```bash
conda env create -f config/environment.yaml
conda activate env3_10
```

The supplied environment uses Python 3.10 and a CUDA-enabled PyTorch build. A compatible NVIDIA GPU and driver are recommended. To run on CPU instead, set `device: 'cpu'` in `config/AFNO.yaml`; CPU inference may be slow.


## Configure a 2023 forecast

Edit the `afno_inference` section in `config/AFNO.yaml`. The following example runs a 24-hour Direct-model forecast initialized at 00:00 UTC on 21 March 2023:

```yaml
afno_inference:
  # Keep the other model-architecture settings supplied in AFNO.yaml.

  device: 'gpu'
  test_data_path: './test/2023'
  static_data_path: './static'
  best_checkpoint_path: './checkpoints/direct_ckpt.tar'

  flow: !!bool False
  n_history: 0
  log_DEN: !!bool False

  prediction_type: 'iterative'
  dt: 1
  n_prediction: 24

  ics_type: 'datetime'
  date_time: '2023-03-21 00:00:00'
  pre_day: 1

  result_save: !!bool True
  pre_resultname: 'direct_20230321_00'
```

Do not replace the entire `afno_inference` section with this shortened example. Retain the architecture and variable settings already present in `config/AFNO.yaml`, including `model_name`, `patch_size`, `depth`, `embed_dim`, `num_blocks`, `in_variables`, `in_drivers`, and `out_variables`.

The forecast initialization must be within 2023 and must leave enough subsequent hourly files for the requested forecast length. For a 24-hour forecast, at least 24 later hourly samples must be available.

### Model-specific changes

For each checkpoint, update the following fields before running the command:

**Direct**

```yaml
best_checkpoint_path: './checkpoints/direct_ckpt.tar'
static_data_path: './static'
flow: !!bool False
n_history: 0
log_DEN: !!bool False
pre_resultname: 'direct_20230321_00'
```

**Flow**

```yaml
best_checkpoint_path: './checkpoints/flow_ckpt.tar'
static_data_path: './static'
flow: !!bool True
n_history: 0
log_DEN: !!bool False
pre_resultname: 'flow_20230321_00'
```

**1-hour history**

```yaml
best_checkpoint_path: './checkpoints/history_1h_ckpt.tar'
static_data_path: './static'
flow: !!bool False
n_history: 1
log_DEN: !!bool False
pre_resultname: 'history_1h_20230321_00'
```

**log-DEN**

```yaml
best_checkpoint_path: './checkpoints/log_den_ckpt.tar'
static_data_path: './static_log'
flow: !!bool False
n_history: 0
log_DEN: !!bool True
pre_resultname: 'log_den_20230321_00'
```

The log-DEN model reads the same processed 2023 test files as the other models. The dataset loader applies `log10` to `DEN` during loading; `static_log` supplies the matching normalization statistics. Do not use the standard `static` statistics with this model.

## Run inference

Run the following command from the project root after updating `config/AFNO.yaml`:

```bash
python eval_tiegcm.py \
  --run_num inference \
  --yaml_config ./config/AFNO.yaml \
  --config afno_inference \
  --weights ./checkpoints/direct_ckpt.tar \
  --override_dir ./inference_output/direct
```

On Windows PowerShell, use one line:

```powershell
python eval_tiegcm.py --run_num inference --yaml_config ./config/AFNO.yaml --config afno_inference --weights ./checkpoints/direct_ckpt.tar --override_dir ./inference_output/direct
```

Replace the checkpoint and output directory for each model. Use a different `pre_resultname` and `--override_dir` for every run to prevent one model's results from overwriting another model's results.

In the current implementation, `--weights` is required when `--override_dir` is supplied, but the model is loaded from `best_checkpoint_path` in `config/AFNO.yaml`. Therefore, keep the `--weights` path and `best_checkpoint_path` identical.

## Output files

For the Direct-model example, the main result is written to:

```text
inference_output/direct/pre_result/direct_20230321_00/result.npz
```

The result archive contains:

- `pred`: normalized autoregressive predictions;
- `real`: normalized reference fields from the 2023 test dataset;
- `rmse`: latitude-weighted RMSE for each lead time and output channel;
- `acc`: latitude-weighted anomaly correlation coefficient;
- `acc_unweighted`: unweighted anomaly correlation coefficient;
- `means` and `stds`: normalization statistics used for the output fields.

An `inference_out.log` file is also created directly inside the directory passed to `--override_dir`. The current script writes `params_index.pkl` in the project working directory.

## Troubleshooting

### No test files are found

Confirm that `test_data_path` points directly to the directory containing the 2023 `.npz` files:

```yaml
test_data_path: './test/2023'
```

### Checkpoint size mismatch

Confirm that the checkpoint is paired with the correct `flow`, `n_history`, and `log_DEN` settings. In particular, the 1-hour-history checkpoint requires `n_history: 1`.

### Incorrect DEN values or statistics

Use `static_log` only with `log_DEN: True`. Use the standard `static` directory for the other three checkpoints.

### `ModuleNotFoundError` for plotting/comparison modules

The two optional modules are absent from the current archive. Follow item 2 under **Important notes about the current source archive**.

### CUDA is unavailable

Use a machine with a compatible NVIDIA GPU and driver, or set:

```yaml
device: 'cpu'
```

## Scope

This repository package supports evaluation and forecasting with supplied pretrained checkpoints. Training and reproduction of the training process are outside the scope of this distribution.
