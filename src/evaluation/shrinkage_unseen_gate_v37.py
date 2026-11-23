"""V37 admission logic. This module has no data decoder or execution backend."""
from dataclasses import dataclass
from pathlib import Path
import re

from .causal_shrinkage_v35 import CANDIDATES, DEVELOPMENT_DATES


SUMMER = ('2021-06-21', '2022-06-21')
WINTER = ('2021-12-21', '2022-12-21')
SEQUENCE = ('identity', 'integration', 'history', 'poison', 'score', 'verify')
FORBIDDEN = frozenset({'GPU', 'DATUM_RELEASE', 'AUTOMATIC_MODEL_START'})
REQUIREMENTS = {
    'identity': (),
    'integration': ('Swarm_identity', 'GFZ_complete', 'season_seed_approved',
                    'model_identity', 'input_frozen', 'sequential_CPU_resources'),
    'history': ('engineering_verified',),
    'poison': ('history_06Z_frozen', 'history_18Z_frozen'),
    'score': ('Swarm_identity', 'history_06Z_frozen', 'history_18Z_frozen',
              'poison_06Z_pass', 'poison_18Z_pass', 'shared_ID_verified', 'no_extrapolation',
              'both_years_history_and_poison_verified', 'pair_once_claim_verified'),
    'verify': ('score_sealed',),
}
CUTOFFS = (6, 18)


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def verify_pins(expected, observed, candidates):
    _require(candidates == dict(CANDIDATES)
             and all(type(v) in (int, float) for v in candidates.values()), 'Candidate identity mismatch')
    _require(bool(expected) and expected == observed
             and all(re.fullmatch('[0-9a-f]{64}', v) for v in expected.values()),
             'Frozen source identity mismatch')


@dataclass(frozen=True)
class StageReceipt:
    day: str
    phase: str
    sha256: str
    outcome: str


def admit(day, phase, *, approved, predecessors=(), evidence=None, operation=None,
          active_model=False, summer_verified=False):
    """Fail closed on supplied, independently authenticated receipts.

    A future worker must authenticate receipt contents and explicit single-phase
    authorizations before using this gate. V37 contains no such worker.
    """
    _require(day not in DEVELOPMENT_DATES and day in SUMMER+WINTER, 'Unseen date not registered')
    _require(phase in SEQUENCE and (day, phase) in approved, 'Separate stage authorization required')
    _require(operation not in FORBIDDEN, 'Forbidden operation')
    expected_op = {'identity': 'METADATA', 'integration': 'CPU_SINGLE_MODEL', 'history': 'HISTORY_ONLY',
                   'poison': 'SYNTHETIC_POISON', 'score': 'FUTURE_ONCE', 'verify': 'READONLY_VERIFY'}
    _require(operation == expected_op[phase], 'Access not authorized for this phase')
    _require(day in SUMMER or phase == 'identity' or summer_verified is True,
             'Winter remains behind the summer pair')
    stage_prefix = SEQUENCE[:SEQUENCE.index(phase)]
    _require(tuple(r.phase for r in predecessors) == stage_prefix
             and all(r.day == day and r.outcome == 'PASS'
                     and re.fullmatch('[0-9a-f]{64}', r.sha256) for r in predecessors),
             'Missing or mismatched stage receipts')
    evidence = evidence or {}
    _require(all(evidence.get(key) is True for key in REQUIREMENTS[phase]), 'Stage evidence incomplete')
    _require(phase != 'integration' or not active_model, 'Concurrent model is forbidden')
    _require(phase != 'integration' or not day.startswith('2022')
             or evidence.get('same_season_2021_integration_verified') is True,
             'The same-season 2021 integration must be independently verified first')
    return True


def claim_score(run_root, day, **admission):
    """Once-only exclusive claim within an operator-provided authorized output directory."""
    admit(day, 'score', **admission)
    root = Path(run_root)
    path = root / day / 'score_once.json'
    _require(root.is_absolute() and path.resolve() == path and path.parent.is_dir(),
             'The bound run root and date directory must be normalized and symlink-free')
    with path.open('x', encoding='utf-8') as receipt:
        receipt.write('{"date":"' + day + '","attempts":1}\n')


def paired_complete(days, pair):
    return pair in (SUMMER, WINTER) and tuple(sorted(days)) == pair


def joint_support(region_counts):
    return ('SUPPORTED' if set(region_counts)=={'low', 'mid', 'high'} and all(
        type(n) is int and n>=30 for n in region_counts.values()) else 'N/A')
