"""Corrected isolated CUDA attempt: set documented CuBLAS contract before torch import."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
from pathlib import Path
import run_fourcastden_training_smoke as worker
worker.F = Path(__file__).resolve().parents[1] / 'experiments/fourcastden_training_smoke_cublas_v2'
if __name__ == '__main__':
    worker.main()
