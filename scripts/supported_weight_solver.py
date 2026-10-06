"""Simultaneous graph solve with immutable per-point legal bone support."""
import math


def project(row, support):
    kept = [value if k in support else 0.0 for k, value in enumerate(row)]
    mass = sum(kept)
    if mass <= 1e-15:
        raise ValueError('EMPTY_LEGAL_WEIGHT_SUPPORT')
    return [value / mass for value in kept], sum(value for k, value in enumerate(row) if k not in support)


def solve_supported(initial, targets, neighbors, domain, supports, anchors,
                    iterations=600, relaxation=.7, fidelity=.35):
    n, dimensions = len(initial), len(initial[0])
    assert len(targets) == n and iterations > 0
    domain = set(domain)
    variable = sorted(domain - set(anchors))
    assert all(1 <= len(supports[i]) <= 4 for i in domain)
    values = [row[:] for row in initial]
    for row in initial + targets + list(anchors.values()):
        assert len(row) == dimensions and all(math.isfinite(x) and x >= 0 for x in row)
        assert abs(sum(row) - 1) < 1e-6
    for i in domain:
        values[i], _ = project(values[i], supports[i])
    for i, row in anchors.items():
        assert i in domain
        values[i], removed = project(row, supports[i])
        assert removed == 0
    residuals, largest_projection = [], 0.0
    for step in range(iterations):
        updated = [row[:] for row in values]
        change = 0.0
        for i in variable:
            total = sum(weight for _, weight in neighbors[i])
            assert total > 0
            average = [sum(values[j][k]*weight for j, weight in neighbors[i])/total for k in range(dimensions)]
            proposed = [(1-relaxation)*values[i][k] + relaxation*(average[k]+fidelity*targets[i][k])/(1+fidelity)
                        for k in range(dimensions)]
            updated[i], removed = project(proposed, supports[i])
            largest_projection = max(largest_projection, removed)
            change = max(change, max(abs(x-y) for x,y in zip(updated[i], values[i])))
        values = updated
        if step in (0, 9, 99, iterations-1):
            residuals.append({'iteration':step+1, 'maximum_component_update':change})
    assert all(sum(x>1e-8 for x in values[i])<=4 and abs(sum(values[i])-1)<1e-6 for i in domain)
    return values, {'iterations':iterations, 'relaxation':relaxation, 'fidelity':fidelity,
                    'residual_samples':residuals, 'maximum_illegal_neighbor_mass_projected':largest_projection,
                    'outside_points_never_written':True, 'projection':'Every iteration, zero disallowed components then normalize legal mass; no last-writer per finger.'}
