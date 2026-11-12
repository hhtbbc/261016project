"""Recover supervision of the SAME running MPI process; never launches a model."""
from pathlib import Path
import os,sys,json,time,signal,datetime,hashlib,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import run_tiegcm_2022_14day as r
F=r.F;OUT=F/'A14';PID=1794822;LOG=ROOT/'logs/tiegcm_2022_14day_A14.log'

def process_table():
    result={}
    for name in os.listdir('/proc'):
        if not name.isdigit():continue
        try:
            p=Path('/proc')/name;s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();status=p.joinpath('status').read_text()
            hwm=next((int(x.split()[1])*1024 for x in status.splitlines() if x.startswith('VmHWM:')),0)
            result[int(name)]=dict(state=s[0],parent=int(s[1]),group=int(s[2]),rss=int(s[21])*os.sysconf('SC_PAGE_SIZE'),hwm=hwm,user_ticks=int(s[11]),system_ticks=int(s[12]),start_ticks=int(s[19]),exit_wait_status=int(s[49]) if len(s)>49 else None)
        except (OSError,ValueError,IndexError):continue
    return result

def safe_rss(pid):
    table=process_table();ids={pid}
    while True:
        new={p for p,x in table.items() if x['parent'] in ids or x['group']==pid}
        if new<=ids:break
        ids|=new
    return sum(table[p]['rss'] for p in ids if p in table)

def main():
    assert not (OUT/'run_status.json').exists() and not (OUT/'guardian_launch_once.json').exists()
    assert Path(f'/proc/{PID}/cwd').resolve()==OUT
    cmd=Path(f'/proc/{PID}/cmdline').read_bytes();assert b'tiegcm2.0' in cmd and b'input.inp' in cmd
    assert json.loads((OUT/'launch_once.json').read_text())['model_launches']==1
    pre=json.loads((OUT/'preflight.json').read_text());assert r.stream_sha(OUT/'input.inp')==pre['input_sha256']
    clock=os.sysconf('SC_CLK_TCK');table=process_table();boot_start=table[PID]['start_ticks']/clock;first_monotonic=time.monotonic();initial_elapsed=first_monotonic-boot_start
    start_utc=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=initial_elapsed)
    launch=dict(attached_pid=PID,actual_model_launches_added=0,reason='original RSS /proc glob ProcessLookupError',initial_process_elapsed_s=initial_elapsed,original_progress=json.loads((OUT/'progress.json').read_text()),budget_clock='original /proc start tick; +10s conservative guard only',exact_launcher_exit_required=True)
    (OUT/'guardian_launch_once.json').open('x').write(json.dumps(launch,indent=2))
    peak=0;hwms={};cpu={};samples=[];checked=set();reason=None;rc=None;raw_exit=None;lastscan=0;lastsize=LOG.stat().st_size;changed=time.monotonic()
    while True:
        table=process_table();p=table.get(PID)
        if p is None:reason=reason or 'launcher_disappeared_without_observable_exit_status';break
        elapsed=time.monotonic()-boot_start
        if p['state']=='Z':
            raw_exit=p['exit_wait_status'];rc=os.waitstatus_to_exitcode(raw_exit) if raw_exit is not None else None;break
        ids={PID}
        while True:
            new={i for i,v in table.items() if v['parent'] in ids or v['group']==PID}
            if new<=ids:break
            ids|=new
        rss=sum(table[i]['rss'] for i in ids if i in table);peak=max(peak,rss)
        for i in ids:
            if i not in table:continue
            hwms[i]=max(hwms.get(i,0),table[i]['hwm']);cpu[i]=[table[i]['user_ticks']/clock,table[i]['system_ticks']/clock]
        if elapsed-lastscan>=1:
            lastscan=elapsed;size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())+LOG.stat().st_size;contents=LOG.read_text(errors='replace')
            if LOG.stat().st_size!=lastsize:lastsize=LOG.stat().st_size;changed=time.monotonic()
            import re,shutil
            if re.search(r'(?im)^.*(?:\bNaN\b|\bInf\b|ERROR|MPI_ABORT).*$',contents):reason='fatal_log_pattern'
            for prefix in ['primary','secondary']:
                paths=sorted(OUT.glob(prefix+'_*.nc'))
                for path in paths[:-1]:
                    if path.name not in checked:
                        try:r.basic_file(path);checked.add(path.name)
                        except Exception as e:reason='completed_volume_check: '+repr(e)
            if size>5*2**30:reason='per_group_output_limit'
            if sum(p.stat().st_size for p in F.rglob('*') if p.is_file())>12*2**30:reason='total_output_limit'
            if any(p.stat().st_size>256*2**20 for p in OUT.glob('*.nc')):reason='volume_size_limit'
            if shutil.disk_usage(ROOT).free<20*2**30:reason='disk_floor'
            if time.monotonic()-changed>120:reason='log_stall'
            row=dict(wall_s=elapsed,rss_bytes=rss,generated_bytes=size,completed_volumes_checked=len(checked),supervision='guardian same original MPI group')
            if not samples or elapsed-samples[-1]['wall_s']>=5:samples.append(row)
            (OUT/'guardian_progress.json').write_text(json.dumps(row)+'\n')
        if elapsed+10>4800:reason='wall_limit_conservative'
        if rss>16*2**30:reason='RSS_limit'
        if reason:
            os.killpg(PID,signal.SIGTERM);time.sleep(2)
            try:os.killpg(PID,signal.SIGKILL)
            except ProcessLookupError:pass
            break
        time.sleep(.1)
    elapsed=time.monotonic()-boot_start
    if rc==0 and reason is None:
        try:
            for path in sorted(OUT.glob('*.nc')):r.basic_file(path)
        except Exception as e:reason='final_volume_check: '+repr(e)
    status=dict(model_launches=1,returncode=rc,stop_reason=reason,elapsed_s=elapsed,started_utc=start_utc.isoformat(),ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),normal_exit_count=LOG.read_text().count('NORMAL EXIT'),peak_sampled_tree_rss_bytes=peak,resource_samples=samples,completed_volumes_checked_online=len(checked),netcdf_bytes=sum(p.stat().st_size for p in OUT.glob('*.nc')),total_generated_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())+LOG.stat().st_size,supervisor_recovered=True,exact_launcher_raw_wait_status=raw_exit,launcher_exit_source='observed /proc stat zombie exit_code; not inferred from log',sum_current_process_lifetime_VmHWM_bytes=sum(hwms.values()),per_pid_lifetime_VmHWM=hwms,sampled_cumulative_cpu_seconds=cpu,children_user_cpu_s=None,children_system_cpu_s=None,rss_note='sampling gap after original supervisor crash; guardian sampled peak is not whole-run peak; per-process lifetime VmHWM retained; no invented waitpid/rusage')
    (OUT/'run_status.json').open('x').write(json.dumps(status,indent=2));print(json.dumps({k:v for k,v in status.items() if k not in ['resource_samples','sampled_cumulative_cpu_seconds','per_pid_lifetime_VmHWM']},indent=2))
    if rc!=0 or reason or status['normal_exit_count']!=4:raise SystemExit(1)
if __name__=='__main__':main()
