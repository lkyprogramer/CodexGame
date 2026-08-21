def topological_layers(graph):
    if not isinstance(graph, dict):
        raise ValueError("graph must be a mapping")
    nodes = set(graph)
    deps = {}
    for node, values in graph.items():
        try:
            current = set(values)
        except TypeError as exc:
            raise ValueError("dependencies must be iterable") from exc
        unknown = current - nodes
        if unknown:
            raise ValueError(f"unknown dependencies: {sorted(map(str, unknown))}")
        deps[node] = current
    remaining = set(nodes)
    layers = []
    while remaining:
        ready = sorted((node for node in remaining if not (deps[node] & remaining)), key=str)
        if not ready:
            blocked = sorted(map(str, remaining))
            raise ValueError("cycle or blocked nodes: " + ", ".join(blocked))
        layers.append(ready)
        remaining.difference_update(ready)
    return layers
