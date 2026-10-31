"""Explicit left/right atmospheric limits; no external datum registration.

Branches are truncated at the event *before* any time interpolation. An ODE
segment must bind its branch, so an endpoint RHS on the left uses the left
atmosphere even though the ordinary query at the event is right-continuous.
"""
import numpy as np
from astropy.time import Time
from .fourcastden_density import FourCastDENDensity


class EventAwareDensity:
    def __init__(self, before, after, event_utc):
        self.event = Time(event_utc, scale='utc')
        if not self.event.isscalar:
            raise ValueError('Scalar UTC event required')
        for field in ('lat', 'lon'):
            if not np.array_equal(getattr(before, field), getattr(after, field)):
                raise ValueError('Branch grids differ')
        self.before = self._truncate(before, left=True)
        self.after = self._truncate(after, left=False)

    def _truncate(self, p, *, left):
        delta = (p.epochs-self.event).sec
        # The physical frame at the event must exist, not be interpolated.
        matches = np.flatnonzero(abs(delta) < 1e-7)
        if len(matches) != 1:
            raise ValueError('Missing unique event frame')
        i = int(matches[0]); sl = slice(None, i+1) if left else slice(i, None)
        if len(p.epochs[sl]) < 2:
            raise ValueError('Missing effective branch prediction frames')
        return FourCastDENDensity(p.epochs[sl], p.lat, p.lon, p.rho[sl]/1000,
            p.height[sl], source=p.source, height_source=p.height_source,
            valid_columns=p.valid[sl], provenance=p.provenance)

    def _choose(self, utc, event_side):
        t = utc if isinstance(utc, Time) else Time(utc, scale='utc')
        if not t.isscalar or event_side not in ('auto', 'left', 'right'):
            raise ValueError('Scalar UTC and auto/left/right required')
        at = bool(t == self.event)
        if event_side != 'auto' and not at:
            raise ValueError('Explicit event side only at exact event UTC')
        left = bool(t < self.event) or (at and event_side == 'left')
        return t, self.before if left else self.after, 'left' if left else 'right'

    def query_native(self, utc, latitude_deg, longitude_deg, altitude_m, *,
                     datum, event_side='auto', vertical='log'):
        t, p, side = self._choose(utc, event_side)
        result = p.query_native(t, latitude_deg, longitude_deg, altitude_m,
                                datum=datum, vertical=vertical)
        result.metadata.update(event_UTC=self.event.isot, event_branch=side,
            event_side_policy='right-continuous; explicit left at event',
            no_cross_event_interpolation=True)
        return result

    def query_pressure(self, utc, latitude_deg, longitude_deg, ilev_index, *,
                       event_side='auto'):
        t, p, side = self._choose(utc, event_side)
        result = p.query_pressure(t, latitude_deg, longitude_deg, ilev_index)
        result.metadata.update(event_UTC=self.event.isot, event_branch=side,
                               no_cross_event_interpolation=True)
        return result

    def density_kg_m3(self, query):
        raise ValueError('EXTERNAL_DATUM_UNVERIFIED')
