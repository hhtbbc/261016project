"""V48 independent replay with the historical P95 tie ordering."""
import numpy as np

import verify_summer_seed_recovery_v47 as adapter


def historical_order_quantile(values, weights):
    """Separate interpolation formula, using the producer's default quicksort order."""
    if not len(values):
        return None
    order = np.argsort(values, kind='quicksort')
    cumulative = np.add.accumulate(weights[order])
    target = .95*cumulative[-1]
    idx = np.searchsorted(cumulative,target)
    if idx == 0:
        return values[order[0]]
    lo,hi = cumulative[idx-1:idx+1]
    a,b = values[order[idx-1:idx+1]]
    return a+(b-a)*(target-lo)/(hi-lo)


def main():
    adapter.independent.quantile = historical_order_quantile
    adapter.main()


if __name__=='__main__':
    main()
