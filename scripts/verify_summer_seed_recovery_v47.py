"""V47 read-only adapter for the independent V46 numerical verifier."""
import verify_summer_seed_sensitivity_v46 as independent
from analyze_summer_seed_recovery_v47 import A, B, RESULT, bind_paths, engineering
import preflight_summer_seed_recovery_v47 as recovery


def main():
    left,right,result = bind_paths(A,B,recovery.OUT)
    assert result == RESULT
    independent.OUT = recovery.OUT
    independent.RUNS = (left,right)
    independent.RESULT = result
    independent.engineering = engineering
    independent.main()


if __name__=='__main__':
    main()
