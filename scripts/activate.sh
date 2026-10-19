# 使用：source /workspace/data/20261016/scripts/activate.sh
_satellite_root=/workspace/data/20261016
if [ "$(realpath "$_satellite_root")" != "$_satellite_root" ]; then
    echo '项目根目录真实路径不符' >&2
    return 1
fi
for _satellite_dir in .tmp .cache .cache/pip .cache/huggingface .cache/torch .cache/matplotlib .cache/pycache .cache/numba; do
    case "$(realpath -m "$_satellite_root/$_satellite_dir")" in
        "$_satellite_root"/*) ;;
        *) echo '缓存路径越界' >&2; return 1 ;;
    esac
done
export TMPDIR="$_satellite_root/.tmp" TMP="$_satellite_root/.tmp" TEMP="$_satellite_root/.tmp"
export XDG_CACHE_HOME="$_satellite_root/.cache" PIP_CACHE_DIR="$_satellite_root/.cache/pip"
export HF_HOME="$_satellite_root/.cache/huggingface" TORCH_HOME="$_satellite_root/.cache/torch"
export MPLCONFIGDIR="$_satellite_root/.cache/matplotlib" NUMBA_CACHE_DIR="$_satellite_root/.cache/numba"
export PYTHONPYCACHEPREFIX="$_satellite_root/.cache/pycache" PYTHONNOUSERSITE=1
export WANDB_DIR="$_satellite_root/logs" WANDB_CACHE_DIR="$_satellite_root/.cache/wandb"
export CUDA_CACHE_PATH="$_satellite_root/.cache/cuda"
source "$_satellite_root/.venv/bin/activate"
unset _satellite_root _satellite_dir
