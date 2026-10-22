import sys,unittest,io,zipfile,tempfile
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fourcastden.multidate import DATES,names_for,BoundedRemoteZip,validate_npz
class Response:
 def __init__(self,status=206,header='bytes 0-2/10',body=b'abc'):self.status=status;self.headers={'Content-Range':header};self.body=body;self.reads=0
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self,n):self.reads+=1;return self.body
class MultidateTests(unittest.TestCase):
 def test_frozen_unique_contiguous_names(self):
  names=[n for d in DATES for n in names_for(d)];self.assertEqual(len(set(names)),12);self.assertFalse(any('2023_01_04' in n for n in names))
  self.assertEqual(names_for(DATES[0]),['2023_03_23_000000.npz','2023_03_23_010000.npz','2023_03_23_020000.npz'])
  with self.assertRaises(ValueError):names_for('2023-01-04')
 def test_accept_exact_206(self):
  x=BoundedRemoteZip('https://example.test/archive',10,opener=lambda *a,**k:Response());self.assertEqual(x.read(3),b'abc');self.assertEqual(x.total,3)
 def test_reject_whole_file_without_body(self):
  r=Response(status=200);x=BoundedRemoteZip('https://example.test/archive',10,opener=lambda *a,**k:r)
  with self.assertRaises(ValueError):x.read(3)
  self.assertEqual(r.reads,0)
 def test_reject_bad_range_without_body(self):
  r=Response(header='bytes 1-3/10');x=BoundedRemoteZip('https://example.test/archive',10,opener=lambda *a,**k:r)
  with self.assertRaises(ValueError):x.read(3)
  self.assertEqual(r.reads,0)
 def test_reject_wrong_body_length(self):
  x=BoundedRemoteZip('https://example.test/archive',10,opener=lambda *a,**k:Response(body=b'ab'))
  with self.assertRaises(ValueError):x.read(3)
 def test_budget_prevents_network_call(self):
  opener=Mock();x=BoundedRemoteZip('https://example.test/archive',10,limit=2,opener=opener)
  with self.assertRaises(ValueError):x.read(3)
  opener.assert_not_called()
 def test_zip_crc_failure_is_not_ignored(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_STORED) as z:z.writestr('sample',b'UNIQUE_TEST_DATA')
  raw=b.getvalue().replace(b'UNIQUE_TEST_DATA',b'BROKEN_TEST_DAT!')
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   with self.assertRaises(zipfile.BadZipFile):z.read('sample')
 def test_existing_real_sample_contract(self):
  q=validate_npz(ROOT/'data/raw/test_minimal_2023/2023_01_04_000000.npz');self.assertEqual(len(q),14);self.assertGreater(q['DEN']['min'],0)
if __name__=='__main__':unittest.main()
