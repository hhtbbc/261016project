"""Prepare a fresh build directory; preserves the original 2.0 source tree."""
from pathlib import Path
import shutil,argparse,re,difflib
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build-tag',default='tiegcm2_build_v1');tag=p.parse_args().build_tag
if not tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in tag):raise ValueError('Invalid tag')
source=ROOT/'third_party/TIEGCM2.0';output=ROOT/'experiments'/tag;prefix=ROOT/'.envs/tiegcm'
for p in [source,output,prefix]:assert p.resolve().is_relative_to(ROOT)
output.mkdir(exist_ok=False)
for name in ['Makefile','mkdepends']:shutil.copy2(source/'scripts'/name,output/name)
shutil.copy2(source/'src/defs5.0',output/'defs.h')
(output/'Srcfiles').write_text('\n'.join(sorted(p.name for p in (source/'src').iterdir() if p.suffix in ['.F','.F90']))+'\n')
(output/'Make.workspace').write_text(f'''F90 = {prefix}/bin/x86_64-conda-linux-gnu-gfortran
MPIF90 = {prefix}/bin/mpifort
MPIRUN = {prefix}/bin/mpirun
FFLAGS = -fdefault-real-8 -fno-range-check
OPTIM = -O2
LIB_NETCDF = {prefix}/lib
INC_NETCDF = {prefix}/include
LIB_ESMF = {prefix}/lib
LIBS = -lnetcdff
.PHONY: prereq
prereq:
\t@true
nchist.o: FFLAGS += -fallow-argument-mismatch
''')
(output/'Make.env').write_text(f'''MAKE_MACHINE = Make.workspace
DIRS = . {source}/src
MPI = TRUE
NPROC = 1
EXECNAME = tiegcm2.0
DEBUG = FALSE
SVN_REVISION = tiegcm2.0
''')
for name,patchname in [('sphpac.F','theta_rank'),('util.F','ieee_constants'),('mud.F','mud_iprm')]:
    before=(source/'src'/name).read_text();after=before
    if name=='sphpac.F':
        for wrapper in ['lfim','lfin']:
            after=re.sub(rf'(      subroutine {wrapper} \([^\n]*\n)',r'\1      dimension theta(*)\n',after,count=1)
    elif name=='util.F':
        after=after.replace('      real :: plus_inf,minus_inf,plus_nanq,minus_nanq,sig_nan','! IEEE binary64 constants; explicit transfer avoids nonstandard BOZ-to-real DATA.')
        for variable,bits in [('plus_inf','7ff0000000000000'),('minus_inf','fff0000000000000'),('plus_nanq','7ff8000000000000'),('minus_nanq','fff8000000000000'),('sig_nan','7ff0000000000001')]:
            after,n=re.subn(rf"      data {variable}\s+/z'{bits}'/[^\n]*",f"      real,parameter :: {variable} =\n     |  transfer(int(z'{bits}',kind=8),0.0_8)",after)
            assert n==1
    else:
        after=after.replace('      integer iprm(16),mgopt(4)','      integer iprm(17),mgopt(4)')
    actual=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/src/'+name,tofile='b/src/'+name))
    assert actual==(ROOT/f'configs/patches/tiegcm2_gfortran12_{patchname}.patch').read_text()
    (output/name).write_text(after)
print(output)
