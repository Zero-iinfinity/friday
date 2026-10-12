"""Validator for the builder's operations JSON.

Every rule it enforces is read from cad_ops_reference.json, so the reference an
LLM sees and the checks that run can never drift apart.

    from cad_validator import validate
    errors, warnings = validate(data)      # build only if `errors` is empty

CLI:
    python cad_validator.py ops.json
"""
import difflib
import json
import sys
from collections import Counter
from pathlib import Path

SPEC_PATH = Path(__file__).with_name("operation_reference.json")
AXIS_VECTORS = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
POSITIONS_BY_KIND = {"line": (1, 2), "circle": (3,)}  # 1 start, 2 end, 3 center
TOL = 1e-9


def load_spec(path=SPEC_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _vec3(v):
    return isinstance(v, list) and len(v) == 3 and all(_num(c) for c in v)


def _hint(word, options):
    m = difflib.get_close_matches(str(word), [str(o) for o in options], n=1)
    return f" (did you mean '{m[0]}'?)" if m else ""


def _profile_problem(g):
    """Return why a sketch is not ONE closed loop, or None if it is."""
    lines, circles = g["lines"], g["circles"]
    if not lines and not circles:
        return "has no non-construction geometry"
    if lines and circles:
        return "mixes lines and circles (a profile must be ONE closed loop)"
    if circles:
        return None if len(circles) == 1 else "has more than one circle (a profile must be ONE closed loop)"
    if len(lines) < 3:
        return "needs at least 3 lines to form a closed loop"

    degree, parent = Counter(), {}

    def find(p):
        parent.setdefault(p, p)
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    for a, b in lines:
        degree[a] += 1
        degree[b] += 1
        parent[find(a)] = find(b)
    loose = [p for p, d in degree.items() if d != 2]
    if loose:
        return f"is not a closed loop: endpoints {loose[:3]} are not shared by exactly two lines"
    if len({find(p) for p in degree}) > 1:
        return "has more than one separate loop (a profile must be ONE closed loop)"
    return None


def _profile_bounds(g):
    xs, ys = [], []
    for a, b in g["lines"]:
        xs += [a[0], b[0]]
        ys += [a[1], b[1]]
    for cx, cy, r in g["circles"]:
        xs += [cx - r, cx + r]
        ys += [cy - r, cy + r]
    return min(xs), max(xs), min(ys), max(ys)


class _Run:
    def __init__(self, spec):
        self.ops = spec["operations"]
        self.caps = spec.get("capabilities", {})
        self.reserved = set(spec.get("reserved_names", []))
        self.reg = {}  # name -> {"kind": shape|sketch|geo|None, "sketch": str, "id": int}
        self.geo = {}  # sketch name -> {"lines": [], "circles": [], "kinds": []}
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    # ---------------------------------------------------------------- document
    def run(self, data):
        if not isinstance(data, dict) or not isinstance(data.get("operations"), list) or not data["operations"]:
            self.errors.append("top level must be an object with a non-empty 'operations' list")
            return
        for k in data:
            if k != "operations":
                self.warnings.append(f"top-level key '{k}' is ignored by the builder")
        for i, op in enumerate(data["operations"]):
            self.op(i, op)

    # --------------------------------------------------------------- one op
    def op(self, i, op):
        if not isinstance(op, dict):
            self.errors.append(f"op[{i}]: must be an object")
            return
        t, name = op.get("type"), op.get("name")
        spec = self.ops.get(t) if isinstance(t, str) else None
        if spec is None:
            self.err(f"op[{i}]", f"unknown or missing 'type' {t!r}{_hint(t, self.ops)}")
            if isinstance(name, str):
                self.reg.setdefault(name, {"kind": None})  # avoid cascading errors
            return
        w = f"op[{i}] {t}"

        reg_name = name
        if not isinstance(name, str) or not name:
            self.err(w, f"'name' must be a non-empty string, got {name!r}")
            reg_name = None
        elif name in self.reserved:
            self.err(w, f"name '{name}' is reserved: it would be mistaken for an axis string")
            reg_name = None
        elif name in self.reg:
            self.err(w, f"duplicate name '{name}' (the later result would silently overwrite the earlier one)")
            reg_name = None

        need = spec.get("requires")
        if need and not self.caps.get(need):
            self.err(w, spec.get("unavailable_reason", f"requires capability '{need}'"))

        params = dict(spec["params"])
        if spec["route"] == "method":
            params = {"target": {"type": "ref", "accepts": [spec["target_type"]], "required": True}, **params}
        args = {k: v for k, v in op.items() if k not in ("type", "name")}
        before = len(self.errors)

        for k in args:
            if k not in params:
                self.err(w, f"unknown argument '{k}'{_hint(k, params)} (the call would raise TypeError)")
        for k, ps in params.items():
            if ps.get("required") and k not in args:
                self.err(w, f"missing required argument '{k}'")

        target = None
        if spec["route"] == "method":
            tn = args.get("target")
            e = self.reg.get(tn) if isinstance(tn, str) else None
            if e and e["kind"] == spec["target_type"]:
                target = e
        for k, v in args.items():
            if k in params:
                self.param(w, k, v, params[k], target, args)

        ok = len(self.errors) == before
        if ok:
            self.semantic(w, t, args)
        self.register(reg_name, spec, args, target, ok)

    # ----------------------------------------------------------- parameters
    def param(self, w, key, v, ps, target, args):
        w = f"{w} '{key}'"
        t = ps["type"]
        if t == "number":
            if not _num(v):
                return self.err(w, f"must be a number, got {v!r}")
            if ps.get("positive") and v <= 0:
                self.err(w, "must be > 0")
            if "min" in ps and v < ps["min"]:
                self.err(w, f"must be >= {ps['min']}")
            if "max" in ps and v > ps["max"]:
                self.err(w, f"must be <= {ps['max']}")
            if ps.get("nonzero") and v == 0:
                self.err(w, "must not be 0")
        elif t == "integer":
            if not _int(v):
                return self.err(w, f"must be an integer, got {v!r}")
            if "min" in ps and v < ps["min"]:
                self.err(w, f"must be >= {ps['min']}")
        elif t == "boolean":
            if not isinstance(v, bool):
                self.err(w, f"must be true or false, got {v!r}")
        elif t == "vec3":
            if not _vec3(v):
                self.err(w, f"must be [x, y, z] (exactly three numbers), got {v!r}")
            elif ps.get("nonzero") and not any(v):
                self.err(w, "must not be [0, 0, 0]")
            elif ps.get("sketch_point") and v[2] != 0:
                self.warn(w, "z should be 0 (sketches are 2D; z is not reliably honoured)")
        elif t == "axis":
            if isinstance(v, str):
                cs = ps.get("case_sensitive", False)
                if (v if cs else v.lower()) not in ps["values"]:
                    only = " (lowercase only)" if cs else ""
                    self.err(w, f"must be one of {ps['values']}{only} or a [x, y, z] vector, got {v!r}")
            elif not (_vec3(v) and any(v)):
                self.err(w, f"must be 'x'/'y'/'z' or a non-zero [x, y, z], got {v!r}")
        elif t == "ref":
            self.ref(w, v, ps)
        elif t == "ref_list":
            need = ps.get("min_items", 1)
            if not isinstance(v, list) or len(v) < need:
                self.err(w, f"must be a list of at least {need} name(s), got {v!r}")
            else:
                for item in v:
                    self.ref(w, item, ps)
        elif t == "geo":
            self.geo_param(w, v, ps, target)
        elif t == "geo_pos":
            if not _int(v) or v not in (1, 2, 3):
                return self.err(w, f"must be 1 (start), 2 (end) or 3 (center), got {v!r}")
            gid = self.geo_id(args.get(ps["for"]), target)
            if gid is not None and target:
                kinds = self.geo[target["sketch"]]["kinds"]
                if 0 <= gid < len(kinds) and v not in POSITIONS_BY_KIND[kinds[gid]]:
                    self.err(w, f"geometry {gid} is a {kinds[gid]}; allowed positions: {POSITIONS_BY_KIND[kinds[gid]]}")
        elif t == "edges":
            items = v if isinstance(v, list) else [v]
            if not items or not all(_int(i) and i >= 0 for i in items) or len(set(items)) != len(items):
                self.err(w, f"must be a non-negative integer or a non-empty list of unique non-negative integers, got {v!r}")
        else:
            self.err(w, f"reference file bug: unknown parameter type '{t}'")

    def ref(self, w, v, ps):
        if not isinstance(v, str):
            return self.err(w, f"must be the name (string) of an earlier operation, got {v!r}")
        e = self.reg.get(v)
        if e is None:
            return self.err(w, f"'{v}' is not defined by an earlier operation{_hint(v, self.reg)}")
        if e["kind"] is None:
            return  # that earlier operation already failed
        if e["kind"] not in ps["accepts"]:
            return self.err(w, f"'{v}' is a {e['kind']}, expected {ps['accepts']}")
        if ps.get("closed_profile") and e["kind"] == "sketch":
            problem = _profile_problem(self.geo[e["sketch"]])
            if problem:
                self.err(w, f"sketch '{v}' {problem}")

    def geo_id(self, v, target):
        if _int(v):
            return v
        e = self.reg.get(v) if isinstance(v, str) else None
        if e and e["kind"] == "geo" and target and e["sketch"] == target["sketch"]:
            return e["id"]
        return None

    def geo_param(self, w, v, ps, target):
        if _int(v):
            gid = v
        elif isinstance(v, str):
            e = self.reg.get(v)
            if e is None:
                return self.err(w, f"'{v}' is not defined by an earlier operation{_hint(v, self.reg)}")
            if e["kind"] is None:
                return
            if e["kind"] != "geo":
                return self.err(w, f"'{v}' is a {e['kind']}, expected a geometry from add_line/add_circle")
            if target and e["sketch"] != target["sketch"]:
                return self.err(w, f"'{v}' belongs to a different sketch than the target")
            gid = e["id"]
        else:
            return self.err(w, f"must be a geometry name or integer id, got {v!r}")
        if target:
            kinds = self.geo[target["sketch"]]["kinds"]
            if not 0 <= gid < len(kinds):
                return self.err(w, f"geometry id {gid} does not exist yet (sketch has {len(kinds)})")
            if "geo_kinds" in ps and kinds[gid] not in ps["geo_kinds"]:
                self.err(w, f"geometry {gid} is a {kinds[gid]}, expected {ps['geo_kinds']}")

    # ------------------------------------------------- cross-argument checks
    def semantic(self, w, t, a):
        if t == "create_cone" and a["r1"] == 0 and a["r2"] == 0:
            self.err(w, "r1 and r2 cannot both be 0")
        elif t == "create_torus" and a["r2"] >= a["r1"]:
            self.warn(w, "r2 (tube) should be smaller than r1 (ring) or the torus self-intersects")
        elif t == "add_line" and a["start"] == a["end"]:
            self.err(w, "start and end are the same point (zero-length line)")
        elif t == "revolve":
            ax = a.get("axis", "z")
            v = AXIS_VECTORS[ax.lower()] if isinstance(ax, str) else ax
            c = a.get("center", [0, 0, 0])
            g = self.geo[self.reg[a["profile"]]["sketch"]]
            if v[0] == 0 and v[1] == 0 and not self.caps.get("sketch_placement"):
                self.err(w, "sketches lie in the XY plane, so revolving about Z gives a flat zero-thickness result; use axis 'x' or 'y'")
            elif v[2] == 0 and 0 in (v[0], v[1]) and c[2] == 0:
                x0, x1, y0, y1 = _profile_bounds(g)
                lo, hi, at = (y0, y1, c[1]) if v[1] == 0 else (x0, x1, c[0])
                if lo + TOL < at < hi - TOL:
                    self.err(w, "profile crosses the revolve axis (self-intersecting solid); keep the whole profile on one side")

    # ---------------------------------------------------------- bookkeeping
    def register(self, name, spec, a, target, ok):
        returns, entry = spec["returns"], {"kind": None}
        if returns == "shape":
            entry = {"kind": "shape"}
        elif returns == "sketch" and spec["route"] == "factory":
            entry = {"kind": "sketch", "sketch": name}
            if name is not None:
                self.geo[name] = {"lines": [], "circles": [], "kinds": []}
        elif returns == "sketch":  # constraint: hands back the same sketch
            if target:
                entry = {"kind": "sketch", "sketch": target["sketch"]}
        elif returns == "geo" and target:
            g = self.geo[target["sketch"]]
            gid = len(g["kinds"])
            g["kinds"].append(spec["geometry"])
            if ok and not a.get("is_construction"):
                if spec["geometry"] == "line":
                    g["lines"].append(tuple(tuple(round(c, 6) for c in a[p][:2]) for p in ("start", "end")))
                else:
                    g["circles"].append((a["center"][0], a["center"][1], a["radius"]))
            entry = {"kind": "geo", "sketch": target["sketch"], "id": gid}
        if name is not None:
            self.reg[name] = entry


def validate(data, spec=None):
    """Return (errors, warnings). Build only when `errors` is empty."""
    run = _Run(spec or load_spec())
    run.run(data)
    return run.errors, run.warnings


def main(argv):
    if len(argv) != 2:
        print("usage: python cad_validator.py ops.json")
        return 2
    with open(argv[1], encoding="utf-8") as f:
        data = json.load(f)
    errors, warnings = validate(data)
    for m in warnings:
        print("WARNING:", m)
    for m in errors:
        print("ERROR:  ", m)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))