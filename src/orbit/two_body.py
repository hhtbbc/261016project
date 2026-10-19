"""SI central gravity and extensible Cartesian state equations."""
import numpy as np

# NGA WGS84 defining parameters (includes atmospheric mass), not GPS-user GM.
# https://earth-info.nga.mil/index.php?action=wgs84&dir=wgs84
EARTH_MU = 3.986004418e14  # m^3/s^2
EARTH_EQUATORIAL_RADIUS = 6378137.0  # m; circle test reference radius


def central_gravity(t, position, velocity, mu=EARTH_MU):
    r = np.asarray(position, dtype=float)
    if r.shape != (3,) or not np.isfinite(r).all() or not np.isfinite(mu) or mu <= 0:
        raise ValueError('Invalid position or gravitational parameter')
    radius = np.linalg.norm(r)
    if radius == 0:
        raise ValueError('Central singularity')
    return -mu * r / radius**3


def make_state_derivative(accelerations):
    """Compose acceleration callables (t_seconds, r_m, v_m_s)."""
    models = tuple(accelerations)
    if not models:
        raise ValueError('At least one acceleration is required')
    def derivative(t, state):
        y = np.asarray(state, dtype=float)
        if y.shape != (6,) or not np.isfinite(y).all():
            raise ValueError('Expected finite six-component state')
        acceleration = np.zeros(3)
        for model in models:
            value = np.asarray(model(t, y[:3], y[3:]), dtype=float)
            if value.shape != (3,) or not np.isfinite(value).all():
                raise ValueError('Invalid acceleration')
            acceleration += value
        return np.concatenate((y[3:], acceleration))
    return derivative


def two_body_rhs(t, state, mu=EARTH_MU):
    return make_state_derivative((lambda t, r, v: central_gravity(t, r, v, mu),))(t, state)


def invariants(states, mu=EARTH_MU):
    y = np.asarray(states)
    return (np.sum(y[..., 3:]**2, axis=-1)/2 - mu/np.linalg.norm(y[..., :3], axis=-1),
            np.cross(y[..., :3], y[..., 3:]))
