"""Minimal single-satellite SP3 c/d PV reader.

Epochs remain naive calendar labels in the declared SP3 time system.
No implicit UTC conversion or reference-frame conversion is performed.
Clock and formal uncertainty fields are deliberately not interpreted.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta
from pathlib import Path
import numpy as np

@dataclass
class SP3Orbit:
    epochs: tuple
    positions_m: np.ndarray
    velocities_m_s: np.ndarray
    satellite_id: str
    time_system: str
    frame: str
    version: str
    interval_s: float
    declared_epochs: int
    orbit_flags: tuple

def read_sp3(path) -> SP3Orbit:
    lines=Path(path).read_text(encoding='ascii').splitlines()
    if not lines or lines[0][:2] not in ('#c','#d'):
        raise ValueError('Only SP3-c/d supported')
    first=lines[0];declared=int(first[32:39]);frame=first[46:51].strip()
    interval=float(next(x for x in lines if x.startswith('##')).split()[3])
    time_line=next(x for x in lines if x.startswith('%c'))
    systems=[x for x in time_line.split() if x in ('GPS','UTC','TAI','GAL','GLO','QZS','BDT')]
    if len(systems)!=1:raise ValueError('Missing or ambiguous time system')
    positions={};velocities={};flags={};epoch=None;epochs=[];identifiers=set()
    for line in lines:
        if line.startswith('*'):
            a=line[1:].split();epoch=datetime(*map(int,a[:5]))+timedelta(seconds=float(a[5]));epochs.append(epoch)
        elif line[:1] in ('P','V'):
            if epoch is None:raise ValueError('PV record before epoch')
            key=line[1:4];identifiers.add(key)
            values=np.array([float(line[i:i+14]) for i in (4,18,32)],dtype=np.float64)
            if not np.isfinite(values).all():raise ValueError('Nonfinite coordinates')
            dest=positions if line[0]=='P' else velocities
            if epoch in dest:raise ValueError('Duplicate record or multiple satellites')
            if line[0]=='P' and (np.all(values==0) or np.any(np.abs(values)>=999999)):
                raise ValueError('Missing position sentinel')
            dest[epoch]=values*(1000 if line[0]=='P' else .1)
            if line[0]=='P':flags[epoch]={'raw_tail':line[74:80],'maneuver':line[78:79] if len(line)>78 else None,'prediction':line[79:80] if len(line)>79 else None}
    if len(identifiers)!=1:raise ValueError('Expected exactly one satellite')
    if len(epochs)!=declared or len(set(epochs))!=declared:raise ValueError('Epoch count mismatch')
    if set(epochs)!=set(positions) or set(epochs)!=set(velocities):raise ValueError('Complete P and V records required')
    if any(abs((b-a).total_seconds()-interval)>1e-6 for a,b in zip(epochs,epochs[1:])):raise ValueError('Irregular or non-increasing epochs')
    return SP3Orbit(tuple(epochs),np.stack([positions[e] for e in epochs]),np.stack([velocities[e] for e in epochs]),next(iter(identifiers)),systems[0],frame,first[1],interval,declared,tuple(flags[e] for e in epochs))
