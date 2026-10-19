"""J2-only acceleration in any Cartesian frame with an explicit symmetry axis.

Constants: IERS Numerical Standards, Paris Observatory useful constants
https://hpiers.obspm.fr/eop-pc/index.php?index=constants&lang=en
mu is unchanged from the project's WGS84 two-body baseline (also listed there).
This is a static nominal J2 model, not an epoch-dependent full geopotential.
"""
import numpy as np
import erfa
import astropy.units as u
from astropy.time import TimeDelta
from scipy.interpolate import CubicSpline
from orbit.two_body import EARTH_MU
from orbit.frames import check_eop

J2_COEFFICIENT = 1.0826359e-3  # dimensionless, unnormalized J2 = -C20
J2_REFERENCE_RADIUS_M = 6378136.6


def _geometry(position, axis, mu, radius, j2):
    r = np.asarray(position, dtype=float)
    k = np.asarray(axis, dtype=float)
    if r.shape != (3,) or k.shape != (3,) or not np.isfinite(r).all() or not np.isfinite(k).all():
        raise ValueError('Expected finite position and axis vectors')
    if not np.isclose(np.linalg.norm(k), 1., rtol=0, atol=1e-12):
        raise ValueError('Symmetry axis must be a unit vector')
    if not np.isfinite([mu, radius, j2]).all() or mu <= 0 or radius <= 0:
        raise ValueError('Invalid gravity constants')
    length = np.linalg.norm(r)
    if length == 0:
        raise ValueError('Central singularity')
    return r, k, length, np.dot(r, k)


def j2_acceleration(position_m, axis=(0., 0., 1.), mu=EARTH_MU,
                    radius_m=J2_REFERENCE_RADIUS_M, j2=J2_COEFFICIENT):
    """Physical perturbing acceleration (m/s²), not rotating-frame d²r/dt².

    a2 = 3 mu J2 R²/(2 r⁵) [(5 (k.r)²/r² - 1) r_vec - 2 (k.r) k].
    No central term, fictitious force, velocity term, or double counting.
    """
    r, k, length, projection = _geometry(position_m, axis, mu, radius_m, j2)
    return 1.5*mu*j2*radius_m**2/length**5 * (
        (5*(projection/length)**2-1)*r - 2*projection*k)


def j2_potential(position_m, axis=(0., 0., 1.), mu=EARTH_MU,
                 radius_m=J2_REFERENCE_RADIUS_M, j2=J2_COEFFICIENT):
    """J2 contribution to specific potential energy (J/kg); force = -grad U."""
    _, _, length, projection = _geometry(position_m, axis, mu, radius_m, j2)
    return mu*j2*radius_m**2/(2*length**3)*(3*(projection/length)**2-1)


def fixed_axis_invariants(states, axis=(0., 0., 1.)):
    """Only for time-independent symmetry axis: total energy and axial h."""
    y = np.asarray(states)
    energy = np.sum(y[:, 3:]**2, axis=1)/2 - EARTH_MU/np.linalg.norm(y[:, :3], axis=1)
    energy += np.array([j2_potential(r, axis) for r in y[:, :3]])
    axial_h = np.cross(y[:, :3], y[:, 3:]) @ np.asarray(axis)
    return energy, axial_h


def terrestrial_z_in_gcrs(times):
    """ITRS figure-axis direction in GCRS: transpose(c2t06a) @ [0,0,1].

    IAU2006/2000A precession/nutation, TT, UT1, frozen IERS-B xp/yp.
    No observed dX/dY correction, consistent with current Astropy transforms.
    This ITRS figure axis is not identified with the CIP or instantaneous omega.
    """
    check_eop(times)
    from astropy.utils import iers
    xp, yp = iers.earth_orientation_table.get().pm_xy(times)
    matrix = erfa.c2t06a(times.tt.jd1, times.tt.jd2, times.ut1.jd1, times.ut1.jd2,
                        xp.to_value(u.rad), yp.to_value(u.rad))
    return matrix[..., 2, :]


class EarthFigureAxis:
    """Bounded cubic interpolation of physical axis directions, never of orbits."""
    def __init__(self, epoch, duration_s, cadence_s=60.):
        if not np.isfinite([duration_s, cadence_s]).all() or duration_s <= 0 or cadence_s <= 0:
            raise ValueError('Positive finite duration and cadence required')
        self.duration_s = float(duration_s)
        self.grid_s = np.linspace(0, duration_s, int(np.ceil(duration_s/cadence_s))+1)
        if len(self.grid_s) < 4:
            raise ValueError('At least four axis samples required')
        self.directions = terrestrial_z_in_gcrs(epoch+TimeDelta(self.grid_s, format='sec'))
        self._spline = CubicSpline(self.grid_s, self.directions, axis=0, extrapolate=False)

    def __call__(self, seconds):
        if not np.isfinite(seconds) or seconds < 0 or seconds > self.duration_s:
            raise ValueError('Axis query outside verified time span')
        k = self._spline(seconds)
        return k/np.linalg.norm(k)

    def acceleration(self, seconds, position, velocity):
        return j2_acceleration(position, self(seconds))
