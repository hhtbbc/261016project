"""Narrow warning provenance channel for read-only audits, never model supervision.

Only the known NetCDF missing_value cast warning from a pinned scientific reader
is routed to a separate raw journal. No data is transformed, no general stderr
is filtered, and unknown warnings fail closed.
"""
from pathlib import Path
import warnings,json,hashlib,os,time,sys
ROOT=Path(__file__).resolve().parents[2]
KNOWN='WARNING: missing_value not used since it cannot be safely cast to variable data type'
class AuditWarningError(RuntimeError):pass

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
class WarningChannel:
 def __init__(self,directory,pinned_readers):
  self.directory=Path(directory);self.directory.resolve().relative_to(ROOT);self.pinned_readers={str(Path(p).resolve()):h for p,h in pinned_readers.items()};self.count=0
 def __enter__(self):
  self.raw=(self.directory/'warnings_raw_local.log').open('x');self.records=(self.directory/'warning_records_local.jsonl').open('x');self.context=warnings.catch_warnings();self.context.__enter__();warnings.simplefilter('always',UserWarning);warnings.showwarning=self.record;return self
 def record(self,message,category,filename,lineno,file=None,line=None):
  self.count+=1;path=str(Path(filename).resolve());text=str(message);norm=' '.join(text.split());pinned=self.pinned_readers.get(path)
  accepted=category is UserWarning and norm==KNOWN and pinned is not None and sha(path)==pinned
  raw=warnings.formatwarning(message,category,filename,lineno,line);self.raw.write(raw);self.raw.flush();os.fsync(self.raw.fileno())
  entry=dict(sequence=self.count,unix=time.time(),category=category.__name__,message=text,source_filename=path,source_lineno=lineno,source_SHA256=sha(path) if Path(path).is_file() else None,classification='KNOWN_NETCDF_CAST_METADATA_WARNING' if accepted else 'UNREVIEWED_WARNING_FAIL_CLOSED',raw_warning_preserved=True)
  self.records.write(json.dumps(entry)+'\n');self.records.flush();os.fsync(self.records.fileno())
  if not accepted:raise AuditWarningError('Unreviewed audit warning; original evidence preserved')
  # Trusted control message intentionally has no free-form warning/source text.
  print(json.dumps(dict(event='AUDIT_METADATA_WARNING_RECORDED',sequence=self.count,category='UserWarning',evidence='separate raw journal; native data gates still mandatory')),flush=True)
 def __exit__(self,kind,value,tb):
  self.context.__exit__(kind,value,tb)
  for f in [self.raw,self.records]:f.flush();os.fsync(f.fileno());f.close()
  return False
