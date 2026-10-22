"""Frozen temporal contract for the four new common-01 UTC windows."""
from datetime import datetime,timedelta
from fourcastden.multidate import DATES
MODELS=('History','Direct','Flow','LogDEN')
ALL_DATES=('2023-01-04',)+DATES

def window_indices(epochs,day,history):
    if day not in DATES:raise ValueError('Only four frozen new dates; January is read-only')
    if type(history) is not int or history not in (0,1):raise ValueError('History must be exactly 0 or 1')
    hours=[datetime.fromisoformat(day)+timedelta(hours=h) for h in range(4)]
    if any(epochs.count(t)!=1 for t in hours):raise ValueError('Four unique real hourly samples required')
    start=epochs.index(hours[0])
    if epochs[start:start+4]!=hours:raise ValueError('Hourly frames must be consecutive and oldest-first')
    return list(range(start+(0 if history else 1),start+4))

def summarize_windows(values):
    """Windows, not grid cells, are the summary units."""
    import numpy as np
    x=np.asarray(values,dtype=float)
    if x.shape!=(5,) or not np.isfinite(x).all():raise ValueError('Exactly five finite window values required')
    return dict(windows=5,mean=float(x.mean()),median=float(np.median(x)),minimum=float(x.min()),maximum=float(x.max()))
