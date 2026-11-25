"""Bind the unchanged V46 science code to verified V46 A and future V47 B."""
from pathlib import Path
import analyze_summer_seed_sensitivity_v46 as legacy
import preflight_summer_seed_recovery_v47 as recovery

A = recovery.OLD / recovery.v46.A
B = recovery.RUN
RESULT = recovery.OUT / 'comparison'


def bind_paths(left, right, root):
    left, right, root = map(Path,(left,right,root))
    recovery.require(left == A and right == B and root == recovery.OUT and
                     all(p.resolve()==p for p in (left,right,root)), 'Wrong V47 analysis pairing')
    return left,right,root/RESULT.name


def engineering():
    left,right,_ = bind_paths(A,B,recovery.OUT)
    recovery.history()
    a = recovery.a_snapshot()
    b = recovery.verify_engineering(right,recovery.protocol())
    recovery.new_identity(b['run_id'],(a['run_id'],recovery.original_failure()['run_id']))
    return [a,b]


def main():
    engineering()
    left,right,result = bind_paths(A,B,recovery.OUT)
    # Process-local binding; frozen V46 code and data are unchanged, all writes in V47.
    legacy.A = str(left)
    legacy.B = str(right)
    legacy.OUT = recovery.OUT
    legacy.RESULT = result
    legacy.main()


if __name__=='__main__':
    main()
