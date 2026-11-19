import unittest,sys,io,zipfile,json,stat
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
from observations.autumn_acquisition import Meter,BudgetError,official,redirect_allowed
from observations.bounded_swarm_acquisition import archive_plan
from observations.autumn_validation import check_product_stem,check_times,source_clock,quality_counts,inspect_initial
from prepare_tiegcm_training_drivers import decode
F=R/'experiments/thermosphere_autumn_data_acquisition_v21/tests_local'
STEM='SW_OPER_DNSAPOD_2__20210923T000000_20210923T235930_0301'
class Contracts(unittest.TestCase):
 def test_budget_receipts_snapshot(self):
  b=Meter(10,20);d=b.summary();b.receive('small',3);self.assertEqual(d['received_transport_bytes']['small'],0)
 def test_budget_reject_overrun(self):
  b=Meter(3,4)
  with self.assertRaises(BudgetError):b.receive('small',4)
  b.receive('small',3);self.assertEqual(b.remaining('small'),0)
 def test_official_https_only(self):
  for u in ['http://kp.gfz.de/app/json/','https://evil.invalid/','https://x:y@kp.gfz.de/']:
   with self.assertRaises(ValueError):official(u,'kp.gfz.de')
 def test_redirect_identity(self):
  u='https://kp.gfz.de/app/json/?start=a&end=b&index=Fobs'
  with self.assertRaises(ValueError):redirect_allowed(u,u.replace('index=Fobs','index=Fadj'))
 def test_wrong_date_version(self):
  check_product_stem(STEM,'2021-09-23')
  for s in [STEM.replace('0301','0302'),STEM.replace('DNSAPOD','DNSBPOD')]:
   with self.assertRaises(ValueError):check_product_stem(s,'2021-09-23')
  with self.assertRaises(ValueError):check_product_stem(STEM,'2022-09-23')
 def test_time_incomplete(self):
  with self.assertRaises(ValueError):check_times(np.array(['2021-09-23T00'],dtype='datetime64[ns]'),'2021-09-23')
 def archive(self,name,members):
  p=F/name
  with zipfile.ZipFile(p,'x') as z:
   for k,v in members:z.writestr(k,v)
  return p
 def test_extra_zip_members(self):
  p=self.archive('extra.zip',[(STEM+'.cdf',b'CDF'),(STEM+'.HDR',b'h'),('extra.txt',b'x')])
  with self.assertRaises(ValueError):archive_plan(p,STEM,1024)
 def test_path_traversal(self):
  p=self.archive('unsafe.zip',[('../'+STEM+'.cdf',b'CDF'),(STEM+'.HDR',b'h')])
  with self.assertRaises(ValueError):archive_plan(p,STEM,1024)
 def test_extract_budget(self):
  p=self.archive('large.zip',[(STEM+'.cdf',b'C'*30),(STEM+'.HDR',b'h')])
  with self.assertRaises(ValueError):archive_plan(p,STEM,20)
 def test_missing_fobs(self):
  with self.assertRaises(ValueError):decode({'datetime':['2022-07-29T00:00:00Z'],'Fobs':[-1]},'Fobs')
 def test_not_definitive(self):
  with self.assertRaises(ValueError):decode({'datetime':['2022-09-07T00:00:00Z'],'Kp':[2.],'status':['pre']},'Kp')
 def test_duplicate_driver(self):
  with self.assertRaises(ValueError):decode({'datetime':['2022-07-29T00:00:00Z']*2,'Fobs':[80,80]},'Fobs')
 def test_quality_invalid_and_unknown(self):
  a=dict(density=np.array([1.,0.,np.nan,1.]),validity_flag=np.array([0,0,0,99]),latitude=np.zeros(4),longitude=np.zeros(4),altitude=np.ones(4));q,x=quality_counts(a);self.assertEqual(q.tolist(),[True,False,False,False]);self.assertEqual(x['unknown_flags'],1)
 def test_source_clock_not_inferred(self):
  self.assertEqual(source_clock([[1,0,0]]),[1,0,0])
  with self.assertRaises(ValueError):source_clock([[266,6,0]])
 def test_bad_initial_missing_states(self):
  p=F/'bad_initial.nc'
  with Dataset(p,'w') as n:n.createDimension('time',1);n.history_type='primary'
  with self.assertRaises(ValueError):inspect_initial(p,p)
 def test_failed_send_charged(self):
  class Broken:
   def send(self,b):raise OSError('test transport failure')
  meter=Meter(10,20)
  with self.assertRaises(OSError):meter.send('small',b'123',Broken())
  self.assertEqual(meter.remaining('small'),7)
 def test_HTTPResponse_buffer_interface(self):
  from observations.autumn_acquisition import TLSStream
  import http.client
  class FakeTLS:
   data=b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}'
   def read(self,n):out=self.data[:n];self.data=self.data[n:];return out
  channel=TLSStream.__new__(TLSStream);channel.sock=None;channel.tls=FakeTLS();channel.operate=lambda call:call();response=http.client.HTTPResponse(channel);response.begin();self.assertEqual(response.status,200);self.assertEqual(response.read(),b'{}');response.close()
if __name__=='__main__':unittest.main()
