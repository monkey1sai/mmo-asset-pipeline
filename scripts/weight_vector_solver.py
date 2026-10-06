"""Bounded screened graph solve for normalized whole skin-weight vectors."""
import math

def solve_vectors(initial, targets, neighbors, domain, anchors, *, iterations=600,
                  relaxation=.7, fidelity=.35):
    n = len(initial)
    dim = len(initial[0])
    assert n and all(len(row) == dim for row in initial+targets)
    assert 0 < relaxation <= 1 and fidelity >= 0 and iterations > 0
    for row in initial+targets+list(anchors.values()):
        assert all(math.isfinite(x) and x >= 0 for x in row)
        assert abs(sum(row)-1) < 1e-6
    domain = set(domain)
    variable = domain-set(anchors)
    outside = set(range(n))-domain
    visited = set()
    components = []
    for seed in sorted(variable):
        if seed in visited:
            continue
        component, boundary, stack = set(), set(), [seed]
        while stack:
            i = stack.pop()
            if i in component:
                continue
            component.add(i)
            for j, w in neighbors[i]:
                assert math.isfinite(w) and w > 0
                if j in variable:
                    if j not in component:
                        stack.append(j)
                else:
                    boundary.add(j)
        assert boundary & (outside | set(anchors)), 'Unanchored component'
        visited |= component
        components.append({'vertices': sorted(component), 'boundary': sorted(boundary)})
    values = [row[:] for row in initial]
    for i, row in anchors.items():
        values[i] = row[:]
    residuals = []
    for step in range(iterations):
        new = [row[:] for row in values]
        maximum = 0.
        for i in sorted(variable):
            total = sum(w for _, w in neighbors[i])
            assert total > 0
            average = [sum(values[j][k]*w for j, w in neighbors[i])/total for k in range(dim)]
            target = [(average[k]+fidelity*targets[i][k])/(1+fidelity) for k in range(dim)]
            new[i] = [(1-relaxation)*values[i][k]+relaxation*target[k] for k in range(dim)]
            maximum = max(maximum, max(abs(a-b) for a,b in zip(new[i],values[i])))
        values = new
        if step in [0, 9, 99, iterations-1]:
            residuals.append({'iteration': step+1, 'maximum_vector_component_update': maximum})
    assert all(all(math.isfinite(x) and x >= 0 for x in row) and abs(sum(row)-1) < 1e-6 for row in values)
    return values, {'iterations': iterations, 'residual_samples': residuals,
                    'components': components, 'maximum_normalization_error': max(abs(sum(r)-1) for r in values)}
