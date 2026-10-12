import FreeCAD as App
import Part
from . import CADShape

AXES = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}


def raw(obj):
    s = getattr(obj, "_shape", obj)
    if getattr(s, "TypeId", "") == "Sketcher::SketchObject":
        s.Document.recompute()
        return s.Shape
    return s

def toWire(obj):
    if isinstance(obj, (list, tuple)):
        return Part.Wire(Part.__sortEdges__([raw(e) for e in obj]))
    s = raw(obj)
    t = s.ShapeType
    if t == "Wire":
        return s
    if t == "Edge":
        return Part.Wire([s])
    if t == "Face":
        return s.OuterWire
    if t in ("Compound", "Shell"):
        return Part.Wire(Part.__sortEdges__(s.Edges))
    raise ValueError("cannot make a wire from " + t)


def toFace(obj):
    if not isinstance(obj, (list, tuple)):
        s = raw(obj)
        if s.ShapeType == "Face":
            return s
    w = toWire(obj)
    if not w.isClosed():
        raise ValueError("profile is not closed")
    return Part.Face(w)


class Feature3D:
    @staticmethod
    def extrude(profile, height, direction=(0, 0, 1)):
        v = App.Vector(*direction)
        v.normalize()
        v.multiply(height)
        return CADShape(toFace(profile).extrude(v))

    @staticmethod
    def revolve(profile, angle=360, axis="z", center=(0, 0, 0)):
        d = AXES[axis] if isinstance(axis, str) else axis
        return CADShape(toFace(profile).revolve(App.Vector(*center), App.Vector(*d), angle))

    @staticmethod
    def sweep(profile, path, frenet=True):
        w = toWire(profile)
        if not w.isClosed():
            raise ValueError("profile is not closed")
        return CADShape(toWire(path).makePipeShell([w], True, frenet))

    @staticmethod
    def loft(profiles, ruled=False, closed=False):
        if len(profiles) < 2:
            raise ValueError("loft needs at least 2 profiles")
        return CADShape(Part.makeLoft([toWire(p) for p in profiles], True, ruled, closed))