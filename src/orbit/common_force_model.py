"""Research-only common Newtonian force; never includes drag or extra J2."""
from orbit.gravity_degree40 import Degree40EarthGravity
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from orbit.third_body_gravity import ThirdBodyGravity

class CommonForceModel:
    def __init__(self, epoch, duration_s, *, degree=40, third_bodies=True):
        self.earth = GcrsSphericalHarmonicsForce(epoch, Degree40EarthGravity(degree))
        self.third = ThirdBodyGravity(epoch, duration_s, sun=third_bodies, moon=third_bodies)
        self.metadata = dict(labels='PROVISIONAL / HINDCAST / FORCE_MODEL_INCOMPLETE',
            frame='GCRS', units='m/s²', degree=degree, order=degree,
            earth_component_count=1, third_bodies=third_bodies,
            ephemeris=self.third.metadata, GM_third_body_m3_s2=self.third.mu,
            missing=['drag','SRP','tides','relativity','actual thrust'],
            truncation_convergence_proven=False)
    def __call__(self, seconds, position, velocity):
        return self.earth(seconds, position, velocity) + self.third(seconds, position, velocity)
