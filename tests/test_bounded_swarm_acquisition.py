"""Synthetic archive/transport tests only, never presented as satellite data."""
from pathlib import Path
import sys,unittest,tempfile,zipfile,io,stat
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from observations.bounded_swarm_acquisition import Budget,archive_plan,download_zip,extract_members,atomic_publish,official_url,posix_cksum
STEM='SW_OPER_DNSAPOD_2__20210323T000000_20210323T235930_0301';URL='https://swarm-diss.eo.esa.int/?do=download'
class Reply(io.BytesIO):
 status=200
 def __init__(self,data,declared=None,url=URL,ctype='application/zip'):super().__init__(data);self.headers={'Content-Length':str(len(data) if declared is None else declared),'Content-Type':ctype};self.url=url
 def geturl(self):return self.url
class Opener:
 def __init__(self,reply):self.reply=reply
 def open(self,req,timeout):assert timeout==25;return self.reply
class AcquisitionTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory(dir=ROOT/'.tmp');self.d=Path(self.t.name)
 def tearDown(self):self.t.cleanup()
 def blob(self,names=None):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   for n in names or [STEM+'.cdf',STEM+'.HDR']:z.writestr(n,b'SYNTHETIC mechanics test, not a CDF')
  return b.getvalue()
 def test_valid_mock_download_extract(self):
  b=self.blob();budget=Budget();r=download_zip(URL,self.d/'a.ZIP',len(b),STEM,budget,opener=Opener(Reply(b)));m=extract_members(self.d/'a.ZIP',STEM,budget,self.d);self.assertTrue(r['CRC_test_PASS']);self.assertEqual(len(m),2);self.assertEqual(budget.network_bytes,len(b))
 def test_host_and_credentials_rejected(self):
  for u in ['http://swarm-diss.eo.esa.int/','https://evil.invalid/','https://user:pw@swarm-diss.eo.esa.int/']:
   with self.assertRaises(ValueError):official_url(u)
 def test_final_redirect_host_rejected(self):
  b=self.blob()
  with self.assertRaises(ValueError):download_zip(URL,self.d/'a.ZIP',len(b),STEM,Budget(),opener=Opener(Reply(b,url='https://evil.invalid/')))
 def test_declared_size_change(self):
  b=self.blob()
  with self.assertRaises(ValueError):download_zip(URL,self.d/'a.ZIP',len(b),STEM,Budget(),opener=Opener(Reply(b,declared=len(b)+1)))
 def test_HTML_rejected(self):
  b=b'<html>not a product</html>'
  with self.assertRaises(ValueError):download_zip(URL,self.d/'a.ZIP',len(b),STEM,Budget(),opener=Opener(Reply(b,ctype='text/html')))
 def test_truncated_body_retained(self):
  b=self.blob()
  with self.assertRaises(ValueError):download_zip(URL,self.d/'a.ZIP',len(b),STEM,Budget(),opener=Opener(Reply(b[:-1],declared=len(b))))
  self.assertTrue((self.d/'a.ZIP.partial').exists());self.assertFalse((self.d/'a.ZIP').exists())
 def test_budget_before_request(self):
  b=self.blob()
  with self.assertRaises(ValueError):download_zip(URL,self.d/'a.ZIP',len(b),STEM,Budget(network_limit=1))
 def test_unsafe_or_extra_names(self):
  for names in [[STEM+'.cdf','../'+STEM+'.HDR'],[STEM+'.cdf',STEM+'.HDR','extra'],[STEM+'.cdf',STEM+'.cdf']]:
   p=self.d/'x.ZIP';p.write_bytes(self.blob(names))
   with self.assertRaises(ValueError):archive_plan(p,STEM,2**20)
 def test_extraction_limit(self):
  p=self.d/'x.ZIP';p.write_bytes(self.blob())
  with self.assertRaises(ValueError):archive_plan(p,STEM,1)
 def test_POSIX_cksum_distinct_from_ZIP_CRC(self):
  import subprocess,zlib
  p=self.d/'bytes';p.write_bytes(b'123456789');crc,n=posix_cksum(p);external=subprocess.check_output(['cksum',str(p)],text=True).split();self.assertEqual(crc,int(external[0]));self.assertEqual(n,9);self.assertNotEqual(crc,zlib.crc32(p.read_bytes()))
 def test_atomic_no_overwrite(self):
  p=self.d/'p';q=self.d/'q';p.write_bytes(b'new');q.write_bytes(b'old')
  with self.assertRaises(FileExistsError):atomic_publish(p,q)
  self.assertEqual(q.read_bytes(),b'old')
 def test_symlink_member_rejected(self):
  p=self.d/'s.ZIP'
  with zipfile.ZipFile(p,'w') as z:
   v=zipfile.ZipInfo(STEM+'.cdf');v.create_system=3;v.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(v,'elsewhere');z.writestr(STEM+'.HDR','x')
  with self.assertRaises(ValueError):archive_plan(p,STEM,2**20)
if __name__=='__main__':unittest.main()
