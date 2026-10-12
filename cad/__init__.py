# cad/__init__.py
from .transforms import Transform
from .patterns import Patterns
from .features import Features
from .boolean import Boolean
from .sketch_constraints import Constraint
from .sketch import SketchGeometry

class CADShape(Transform, Patterns, Features, Boolean):
    def __init__(self, _shape):
        self._shape = _shape

class CADSketch(SketchGeometry, Constraint):
    def __init__(self, _shape):
        self._shape = _shape

from .primitives import Primitives
from .feature_creation import Feature3D
from .sketch import Sketch
from .exporter import Exporter