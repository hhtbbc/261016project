"""Rebuild and run the standalone GPI reader, without any model integration."""
from pathlib import Path
import subprocess,os,argparse
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--log-tag',required=True);a=p.parse_args()
if not a.log_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.log_tag):raise ValueError('Invalid tag')
b=ROOT/'experiments/tiegcm2_apex2023_v1';d=ROOT/'experiments/tiegcm2023_field_check'
log=ROOT/'logs'/f'{a.log_tag}.log'
if log.exists():raise FileExistsError(log)
assert Path(os.environ['TMPDIR']).resolve().is_relative_to(ROOT)
line=[x for x in (ROOT/'logs/apex2023_build.log').read_text().splitlines() if ' -o tiegcm2.0 ' in x][-1]
libs=line.split(' -lnetcdff',1)[1]
executable=d/f'gpi_reader_{a.log_tag}'
if executable.exists():raise FileExistsError(executable)
cmd=['mpifort','-ffree-line-length-none','-fdefault-real-8','-I'+str(b),str(d/'gpi_read_corrected.f90')]+[str(x) for x in sorted(b.glob('*.o')) if x.name!='tgcm.o']+['-lnetcdff']+libs.split()+['-o',str(executable)]
with log.open('x') as f:
    subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(executable)],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=15,check=True)
if 'bad isec_req' in log.read_text():raise RuntimeError('Invalid consumer query')
print(log)
