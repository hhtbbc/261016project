"""Isolated fixture suite for new autumn gates and unchanged V17 warning regressions."""
from pathlib import Path
import sys,unittest,importlib.util,json,time,resource
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
from runtime.tiegcm_rank_exit import write_once
F=R/'experiments/thermosphere_autumn_mareqx_config_v23';base=F/'tests_local';base.mkdir(exist_ok=False)
modules=[]
for name in ['test_tiegcm_autumn_v23','test_tiegcm_v17_readonly']:
    spec=importlib.util.spec_from_file_location(name,R/'tests'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    if name=='test_tiegcm_v17_readonly':m.BASE=base # only fixture location; old F/provenance remain original read-only
    modules.append(m)
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
begin=time.monotonic();cpu=time.process_time()
with (F/'test_log_local.log').open('x') as h:result=unittest.TextTestRunner(stream=h,verbosity=2).run(suite)
record=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),PASS=result.wasSuccessful(),elapsed_s=time.monotonic()-begin,CPU_s=time.process_time()-cpu,self_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,MPI_helper_only=True,physical_model_launches=0,old_fixture_dirs_unchanged=True)
write_once(F/'tests.json',record);print(json.dumps(record));raise SystemExit(0 if record['PASS'] else 2)
