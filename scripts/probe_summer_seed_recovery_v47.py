"""Compile an isolated read-only harness with verbatim frozen path routines."""
from pathlib import Path
import os
import shutil
import subprocess

import preflight_summer_seed_recovery_v47 as r
from atmosphere.restart_validation import REQUIRED

TESTS = r.OUT / 'tests'
CWD = r.OUT / 'probe_cwd'
TREE = r.ROOT / 'third_party/TIEGCM2.0/src'

PROGRAM = """
program v47_readonly
  use, intrinsic :: ieee_arithmetic
  implicit none
  include 'netcdf.inc'
  character(1024) :: source, gpi_ncfile, label, gswm_mi_di_ncfile, gswm_mi_sdi_ncfile, path
  character(1024) :: output(17), secout(16)
  character(16) :: potential_model, secflds(99)
  integer :: start_year,start_day,calendar_advance,source_start(3),start(3),stop(3),step,hist(3)
  integer :: mxhist_prim,secstart(3),secstop(3),sechist(3),mxhist_sech,calc_helium
  character(120) :: diskfile
  character(16) :: fields(34)
  integer :: ncid, i, j, nd, dims(8), l, count, kind, vid, clock(3), year(1), day(1)
  real(8), allocatable :: values(:)
  namelist /tgcm_input/ label,start_year,start_day,calendar_advance,source,source_start,start,stop, &
    step,hist,output,mxhist_prim,secstart,secstop,sechist,secout,mxhist_sech,secflds, &
    gswm_mi_di_ncfile,gswm_mi_sdi_ncfile,potential_model,calc_helium,gpi_ncfile
  call get_command_argument(1,path)
  open(unit=10,file=trim(path),status='old',action='read')
  read(10,nml=tgcm_input)
  close(10)
  if (start_year/=2022.or.start_day/=158.or.step/=60.or.any(start/=[158,0,0]).or.any(stop/=[174,0,0])) stop 70
  if (any(source_start/=[172,0,0]).or.any(start(2:3)/=source_start(2:3))) stop 71
  call expand_path(source)
  call expand_path(gpi_ncfile)
  inquire(file=trim(gpi_ncfile),exist=probe_gpi_exists)
  if (.not.probe_gpi_exists) stop 72
  print '(a,i0)', 'SOURCE_EXPANDED_LENGTH=',len_trim(source)
  ! The same 120-character local and call sequence from rdsource.F.
  diskfile=' '
  call getfile(source,diskfile)
  print '(a,i0)', 'RDSOURCE_DISKFILE_LENGTH=',len_trim(diskfile)
  print '(a,a)', 'RDSOURCE_DISKFILE=',trim(diskfile)
  call nc_open(ncid,diskfile,'OLD','READ')
  if (ncid==0) stop 73
  call ck(nf_inq_varid(ncid,'year',vid))
  call ck(nf_get_var_int(ncid,vid,year))
  call ck(nf_inq_varid(ncid,'day',vid))
  call ck(nf_get_var_int(ncid,vid,day))
  call ck(nf_inq_varid(ncid,'mtime',vid))
  call ck(nf_get_var_int(ncid,vid,clock))
  if (year(1)/=2002.or.day(1)/=172.or.any(clock/=source_start)) stop 74
  fields=[character(16) :: &
    @FIELDS@]
  do i=1,size(fields)
    call ck(nf_inq_varid(ncid,trim(fields(i)),vid))
    call ck(nf_inq_vartype(ncid,vid,kind))
    call ck(nf_inq_varndims(ncid,vid,nd))
    if (kind/=NF_DOUBLE.or.nd<3.or.nd>4) stop 75
    call ck(nf_inq_vardimid(ncid,vid,dims))
    count=1
    do j=1,nd
      call ck(nf_inq_dimlen(ncid,dims(j),l))
      if (l<1.or.l>72) stop 76
      count=count*l
    enddo
    if (count>75168) stop 77
    allocate(values(count))
    call ck(nf_get_var_double(ncid,vid,values))
    if (.not.all(ieee_is_finite(values)).or.all(abs(values)>1d30)) stop 78
    deallocate(values)
    print '(a,a,1x,i0)', 'FIELD_READ=',trim(fields(i)),count
  enddo
  call ck(nf_close(ncid))
  print '(a,i0,1x,i0,1x,3i5)', 'NATIVE_CLOCK=',year,day,clock
  print '(a)', 'READONLY_SEED_PASS'
contains
  subroutine ck(status)
    integer,intent(in) :: status
    if (status/=NF_NOERR) then
      print '(a)', NF_STRERROR(status)
      stop 79
    endif
  end subroutine
end program
subroutine handle_ncerr(status,message)
  implicit none
  integer,intent(in) :: status
  character(*),intent(in) :: message
  print '(a,i0,1x,a)', 'NETCDF_ERROR=',status,message
  stop 80
end subroutine
subroutine shutdown(message)
  implicit none
  character(*),intent(in) :: message
  print '(a)',message
  stop 81
end subroutine
"""


def exact_block(path, first, last):
    text = path.read_text()
    a = text.index(first)
    b = text.index(last,a)+len(last)
    return text[a:b]+'\n'


def main():
    r.require(TESTS.resolve()==TESTS and CWD.resolve()==CWD and r.absent(r.RUN),'Unexpected probe directory')
    CWD.mkdir(exist_ok=True)
    r.require(not any(CWD.iterdir()), 'Probe CWD must remain empty')
    r.seed_path(CWD,r.SOURCE)
    paths = ('getfile.F','util.F','nchist.F','rdsource.F')
    manifest = r.load(r.v45.OUT/'preflight.json')['critical_assets']
    for name in paths:
        path = TREE/name
        r.require(r.sha(path)==manifest[str(path.relative_to(r.ROOT))], 'Frozen Fortran code drift')
    getfile = (TREE/'getfile.F').read_text()
    expand = exact_block(TREE/'util.F','      recursive subroutine expand_path(path)','      end subroutine expand_path')
    ncopen = exact_block(TREE/'nchist.F','      subroutine nc_open(ncid,flnm,status,rdwr)','      end subroutine nc_open')
    # Restore module-scope declarations around the extracted external routine.
    head, body = ncopen.split("\n", 1)
    ncopen = head + "\n      implicit none\n      include 'netcdf.inc'\n" + body
    rd = exact_block(TREE/'rdsource.F',"      diskfile = ' '","      call nc_open(ncid,diskfile,'OLD','READ')")
    fixed = TESTS/'frozen_probe_routines.f'
    program = TESTS/'seed_probe.f90'
    binary = TESTS/'seed_probe_local'
    fields = ', &\n    '.join(','.join(repr(k) for k in REQUIRED[i:i+6]) for i in range(0,len(REQUIRED),6))
    source = PROGRAM.replace("  character(120) :: diskfile","  logical :: probe_gpi_exists\n  character(120) :: diskfile")
    start = source.index("  diskfile=' '")
    end = source.index("  if (ncid==0)",start)
    rd = rd.replace('filepath','source')
    # Keep the exact call and buffer; instrument the returned path before nc_open.
    rd = rd.replace("      call nc_open", "      print '(a,i0)', 'RDSOURCE_DISKFILE_LENGTH=',len_trim(diskfile)\n"
        "      print '(a,a)', 'RDSOURCE_DISKFILE=',trim(diskfile)\n      call nc_open")
    source = (source[:start]+"  call v47_acquire(source,ncid)\n"+source[end:]).replace('@FIELDS@',fields)
    getfile_unit = TESTS/'frozen_getfile.f'
    with getfile_unit.open('x') as f:
        f.write(getfile)
    with fixed.open('x') as f:
        f.write(expand+ncopen+
                "      subroutine v47_acquire(source,ncid)\n"
                "      implicit none\n"
                "      character(len=*),intent(in) :: source\n"
                "      integer,intent(out) :: ncid\n"
                "      character(len=120) :: diskfile\n"+rd+"      end subroutine\n")
    with program.open('x') as f:
        f.write(source)
    stack = r.ROOT/'.envs/tiegcm'
    compiler = stack/'bin/x86_64-conda-linux-gnu-gfortran'
    env = r.v46.env.runtime_environment()
    subprocess.run([str(compiler),'-ffixed-line-length-132','-I'+str(stack/'include'),str(fixed),str(getfile_unit),
                    str(program),'-L'+str(stack/'lib'),'-lnetcdff','-lnetcdf','-o',str(binary)],
                   cwd=TESTS,env=env,check=True,timeout=60)
    linked = subprocess.check_output(['ldd',str(binary)],env=env,text=True)
    r.require('not found' not in linked and str(stack/'lib/libnetcdff.so.7') in linked,'Probe library mismatch')
    lib_sha = r.sha(stack/'lib/libnetcdff.so.7')
    r.require(lib_sha==r.load(r.v45.OUT/'preflight.json')['netcdff_sha256'],'NetCDF-Fortran drift')
    old = r.OLD/f'{r.v46.B}.namelist'
    def probe(name,path,cwd):
        result = subprocess.run([str(binary),str(path)],cwd=cwd,env=env,
                  capture_output=True,text=True,timeout=45)
        with (TESTS/f'{name}.txt').open('x') as f:
            f.write(result.stdout+result.stderr)
        return result.returncode,result.stdout+result.stderr
    short, result = probe('short_source',r.INPUT,CWD)
    r.require(short==0 and 'READONLY_SEED_PASS' in result and
              'SOURCE_EXPANDED_LENGTH=10' in result and 'RDSOURCE_DISKFILE_LENGTH=10' in result and
              result.count('FIELD_READ=')==34,'Real source read failed')
    long, text = probe('legacy_truncation',old,CWD)
    r.require(long!=0 and 'SOURCE_EXPANDED_LENGTH=147' in text and 'RDSOURCE_DISKFILE_LENGTH=120' in text
              and 'End of record' in text,'Legacy failure not reproduced')
    wrong, text = probe('wrong_cwd',r.INPUT,r.ROOT)
    r.require(wrong!=0 and 'could not find file ../seed.nc' in text,'Wrong cwd did not fail')
    r.write(TESTS/'fortran_probe.json',{'short_exit':short,'old_exit':long,'wrong_cwd_exit':wrong,
        'old_expanded_bytes':147,'diskfile_capacity':120,'short_chars':10,
        'required_fields_read':34,'source_clock':[172,0,0],'native_year':2002,'native_day':172,
        'seed_sha256':r.sha(r.SEED),'libnetcdff_sha256':lib_sha,'cwd_contract':'sibling of planned run',
        'full_model_loaded':False,'mpi_jobs':0,'physics_steps':0})


if __name__=='__main__':
    main()
