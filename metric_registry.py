
import json

class MetricRegistry:
    def __init__(self, path: str):
        with open(path, 'r') as f:
            self._m = json.load(f)
    def get(self, name: str):
        return self._m.get(name)
    def names(self):
        return list(self._m.keys())
    def render(self, name: str, params: dict):
        spec = self.get(name)
        if not spec:
            raise KeyError(f"Unknown metric: {name}")
        required = spec.get("params", [])
        missing = [p for p in required if p not in params]
        if missing:
            raise ValueError(f"Missing params: {missing}")
        return spec["sql"], {k: params[k] for k in required}
