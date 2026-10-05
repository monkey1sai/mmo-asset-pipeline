"""Small numerical helpers for reversible pre-skin corrective construction."""
import numpy as np


def smoothstep(low, high, value):
    t = min(1., max(0., (value-low)/(high-low)))
    return t*t*(3.-2.*t)


def inverse_delta(matrix, posed_delta, condition_limit=20):
    matrix = np.asarray(matrix, dtype=float)
    delta = np.asarray(posed_delta, dtype=float)
    condition = float(np.linalg.cond(matrix))
    if not np.isfinite(condition) or condition > condition_limit:
        raise ValueError('UNSTABLE_INVERSE_SKIN')
    result = np.linalg.solve(matrix, delta)
    if not np.all(np.isfinite(result)):
        raise ValueError('NONFINITE_CORRECTIVE')
    return result, condition


def surface_limited_magnitude(desired, gap, alignment, clearance=.0008):
    if alignment <= .1:
        return 0.
    return min(desired, max(0., (gap-clearance)/alignment))
