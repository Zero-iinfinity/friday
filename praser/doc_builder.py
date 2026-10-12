import FreeCAD as App

BOOL = {
    "union": "Part::Fuse",
    "cut": "Part::Cut",
    "intersection": "Part::Common",
}


def vec(p):
    return p if isinstance(p, App.Vector) else App.Vector(*p)


def place(o, op):
    o.Placement = App.Placement(vec(op.get("position", (0, 0, 0))), App.Rotation())


def snap(doc, name, s):
    o = doc.addObject("Part::Feature", name)
    o.Shape = s._shape
    return o

SKETCH_OPS = {
    "add_line", "add_circle", "coincident", "horizontal", "vertical",
    "parallel", "perpendicular", "tangent", "equal", "pointOnObject",
    "symmetric", "block", "distance", "distanceX", "distanceY",
    "radius", "diameter", "angle",
}
def build_document(doc, ops, shapes):
    objs = {}


    for op in ops:
        t = op["type"]
        if t in SKETCH_OPS:
            continue
        n = op["name"]
        if n not in shapes:
            continue
        s = shapes[n]

        if t == "create_sketch":
            s._shape.Label = n
            objs[n] = s._shape
            continue

        o = None

        if t == "create_box":
            o = doc.addObject("Part::Box", n)
            o.Length = op["length"]
            o.Width = op["width"]
            o.Height = op["height"]
            place(o, op)
        elif t == "create_cylinder":
            o = doc.addObject("Part::Cylinder", n)
            o.Radius = op["radius"]
            o.Height = op["height"]
            place(o, op)
        elif t == "create_cone":
            o = doc.addObject("Part::Cone", n)
            o.Radius1 = op["r1"]
            o.Radius2 = op["r2"]
            o.Height = op["height"]
            place(o, op)
        elif t == "create_sphere":
            o = doc.addObject("Part::Sphere", n)
            o.Radius = op["radius"]
            place(o, op)
        elif t == "create_torus":
            o = doc.addObject("Part::Torus", n)
            o.Radius1 = op["r1"]
            o.Radius2 = op["r2"]
            place(o, op)
        elif t in BOOL:
            a = objs.get(op["target"])
            b = objs.get(op["other"])
            if a is not None and b is not None:
                o = doc.addObject(BOOL[t], n)
                o.Base = a
                o.Tool = b
        elif t == "extrude":
            sk = objs.get(op["profile"])
            if sk is not None and sk.TypeId == "Sketcher::SketchObject":
                d = vec(op.get("direction", (0, 0, 1)))
                d.normalize()
                o = doc.addObject("Part::Extrusion", n)
                o.Base = sk
                o.DirMode = "Custom"
                o.Dir = d
                o.LengthFwd = op["height"]
                o.Solid = True

        if o is None:
            o = snap(doc, n, s)

        o.Label = n
        objs[n] = o

    doc.recompute()

    for o in doc.Objects:
        if "Invalid" in o.State:
            print(f"DOC WARNING: {o.Name} failed to recompute")

    return objs