"""Independently replay the complete late N2 gate grid from raw history."""
from datetime import timedelta
import unittest
from collections import Counter

from netCDF4 import Dataset, num2date
import numpy as np

import diagnose_summer_n2_residual_v52 as d


def require_schema(dimensions,unit):
    if dimensions!=('time','lev','lat','lon') or unit!='mmr':
        raise ValueError('Wrong N2 schema')


def independent_mask(x,y):
    keep=np.isfinite(x)&np.isfinite(y)&(np.abs(x)>1e-8)
    ok=np.zeros(x.shape,bool)
    ok[keep]=np.abs((y[keep]-x[keep])/x[keep])<.05
    return keep,ok


def read(paths,utc):
    hours=(utc-d.v.gpi.START).total_seconds()/3600
    volume,i=divmod(int(hours)-1,24)
    fields=[]
    species=[]
    zgs=[]
    for directory in paths:
        with Dataset(directory/f'secondary_{volume+1:03d}.nc') as n:
            t=n['time']
            if num2date(t[i],t.units).isoformat()!=utc.replace(tzinfo=None).isoformat():
                raise ValueError('Wrong time index')
            k=n['N2']
            require_schema(k.dimensions,k.units)
            k.set_auto_mask(False)
            x=np.asarray(k[i],dtype=float)
            for attr in ('missing_value','_FillValue'):
                if attr in k.ncattrs():
                    x[np.isin(x,np.asarray(k.getncattr(attr),dtype=k.dtype))]=np.nan
            x[abs(x)>1e30]=np.nan
            fields.append(x)
            species.append(np.stack([np.asarray(n[name][i],dtype=float) for name in d.COMP]))
            zgs.append(np.asarray(n['ZG'][i],dtype=float)*1e-5)
            lev=np.asarray(n['lev'][:])
            ilev=np.asarray(n['ilev'][:])
            lat=np.asarray(n['lat'][:])
    return fields,lat,species,zgs,lev,ilev


def main():
    paths,ids=d.identity()
    published={ (r['UTC'],r['region'],int(r['level'])):r for r in d.csv_rows(d.V51/'same_UTC_native_gates.csv')
                if r['variable']=='N2'}
    result={(r['UTC'],r['region'],int(r['level'])):r for r in d.csv_rows(d.OUT/'failures.csv')}
    unique=Counter()
    failed=set()
    checks=0
    rules=d.run.load(d.v.science.RULES)
    for t in d.v.LATE_UTC:
        (a,b),lat,com,zgs,lev,ilev=read(paths,t)
        closure=(b-a)+np.sum(com[1]-com[0],axis=0)
        qround=sum(np.abs(np.spacing(w.astype('f4'))).astype(float) for w in (a,b,*com[0],*com[1]))/2
        brackets={k:next((j for j in range(len(ilev)-1) if ilev[j]<=z<ilev[j+1]),None)
                  for k,z in enumerate(lev)}
        keep,ok=independent_mask(a,b)
        union=np.zeros(a.shape,bool)
        for area,(lo,hi) in rules['latitude_regions'].items():
            m=(lat>=lo)&(lat<=hi)
            for level in range(a.shape[0]):
                key=(t.isoformat(),area,level)
                row=published[key]
                n=np.count_nonzero(keep[level,m])
                passes=np.count_nonzero(ok[level,m])
                assert n==int(row['n_21'])
                assert n and passes/n==float(row['fraction_21'])
                assert (passes/n>=.95)==(row['gate_21']=='True')
                checks+=1
                if passes/n>=.95:
                    continue
                failed.add(key)
                r=result[key]
                assert passes==int(r['passed'])
                x,y=a[level,m],b[level,m]
                bad=keep[level,m]&~ok[level,m]
                union[level,m]|=bad
                err=abs(closure[level,m][bad])
                assert np.max(err)==float(r['residual_error_max'])
                assert int((err<=qround[level,m][bad]+4e-15).sum())==int(r['residual_within_output_rounding'])
                j=brackets[level]
                for label,z in zip('AB',zgs):
                    if j is None:
                        assert r[f'{label}_ZG_min_km']==r[f'{label}_ZG_max_km']==''
                    else:
                        w=(lev[level]-ilev[j])/(ilev[j+1]-ilev[j])
                        column=(1-w)*z[j,m]+w*z[j+1,m]
                        assert np.isclose(column[keep[level,m]].min(),float(r[f'{label}_ZG_min_km']))
                delta=abs(y-x)
                rel=delta[keep[level,m]]/abs(x[keep[level,m]])
                assert np.isclose(np.percentile(rel,95),float(r['relative_P95']),rtol=1e-14)
                assert np.isclose(np.max(rel),float(r['relative_max']),rtol=1e-14)
        x,y=a[union],b[union]
        af=np.abs(x-d.MODEL_FLOOR)<=d.FLOOR_TOL
        bf=np.abs(y-d.MODEL_FLOOR)<=d.FLOOR_TOL
        unique.update(both_fail=int((af&bf).sum()),A_only_fail=int((af&~bf).sum()),
                      B_only_fail=int((~af&bf).sum()),neither_fail=int((~af&~bf).sum()))
    assert len(failed)==118 and failed==set(result)
    stats=d.run.load(d.OUT/'diagnostics.json')
    assert unique==stats['unique_failed_grid_hours']
    assert Counter(r for _,r,_ in failed)=={'global':2,'south_polar':28,'south_mid':64,'tropics':24}
    assert d.run.load(d.V51/'result.json')['science']=='SEED_SENSITIVITY_FAIL'
    tests=unittest.TestSuite()
    class Contracts(unittest.TestCase):
        def test_bad_units(self):
            with self.assertRaises(ValueError): require_schema(('time','lev','lat','lon'),'kg')
        def test_bad_vertical(self):
            with self.assertRaises(ValueError): require_schema(('time','ilev','lat','lon'),'mmr')
        def test_reference_and_threshold(self):
            keep,ok=independent_mask(np.array([1e-8,100.,95.,1.01e-8]),np.array([1e-8,105.,100.,1.01e-8]))
            np.testing.assert_array_equal(keep,[False,True,True,True])
            np.testing.assert_array_equal(ok,[False,False,False,True])
            self.assertTrue(19/20>=.95)
            self.assertFalse(18/20>=.95)
        def test_bad_utc(self):
            with self.assertRaises(ValueError): read(paths,d.v.LATE_UTC[0]+timedelta(minutes=1))
        def test_sha(self):
            with self.assertRaises(ValueError):
                d.v.gpi.verify_sha(d.v.gpi.FILE,'0'*64)
        def test_published_rules(self):
            self.assertEqual(rules['composition_relative_limit'],.05)
            self.assertEqual(rules['trace_reference_floor_mmr'],1e-8)
            self.assertEqual(rules['minimum_fraction_within_limits'],.95)
        def test_unseen_target_rejection(self):
            from audit_summer_assets_v38 import sealed_read
            with self.assertRaises(ValueError):
                sealed_read(object(),'density',[])
        def test_scope(self):
            for path in paths:
                self.assertEqual(path.parent,d.v.OUT)
                self.assertIn(path.name,d.v.offline.RUNS)
            claim=d.run.OUT/'claim_A.json'
            self.assertTrue(claim.is_file())
            self.assertFalse(d.run.available('A'))
            self.assertFalse(d.run.available('B'))
    tests.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    tested=unittest.TextTestRunner().run(tests)
    if not tested.wasSuccessful():
        raise ValueError('Independent negative tests failed')
    d.run.write_once(d.OUT/'independent_full.json',dict(gates=checks,failing_keys=len(failed),unique_failed_grid_hours=unique,
                  tests=tested.testsRun,identity=ids,unseen_Swarm_reads=0,model_runs=0,GPU=0))


if __name__=='__main__':
    main()
