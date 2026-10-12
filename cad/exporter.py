from pathlib import Path


def _getattr(obj):
    return getattr(obj, "_shape", obj)


class Exporter:
    def __init__(self, _shape):
        self._shape = _getattr(_shape)

    def _prep(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)

    def exportStep(self, path):
        p = self._prep(path)
        self._shape.exportStep(p)
        return p

    def exportStl(self, path):
        p = self._prep(path)
        self._shape.exportStl(p)
        return p