"""
Geometry-level validation for the Word-to-CAD pipeline.

This module is intentionally separate from schema.py.

schema.py answers:
    "Is the JSON structurally and semantically valid?"

geometry.py answers:
    "Does the actual FreeCAD geometry make sense?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEOMETRY_TOL = 1e-7
VOLUME_TOL = 1e-9

BOOLEAN_CUT_NAMES = {
    "cut",
    "boolean_cut",
}

BOOLEAN_COMMON_NAMES = {
    "common",
    "intersection",
    "boolean_common",
}

BOOLEAN_FUSE_NAMES = {
    "union",
    "fuse",
    "boolean_union",
}

FILLET_NAMES = {
    "fillet",
}

CHAMFER_NAMES = {
    "chamfer",
}


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------

@dataclass
class GeometryResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warning(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")


# ---------------------------------------------------------------------------
# FreeCAD helpers
# ---------------------------------------------------------------------------

def _unwrap_shape(obj: Any) -> Any:
    """
    Return a FreeCAD Part.Shape from either:
        - a raw Part.Shape
        - a project wrapper with `.s` or `._shape`
        - an object exposing `.Shape`
    """
    if obj is None:
        return None

    # Project wrapper used by the existing CAD abstraction.
    shape = getattr(obj, "s", None)
    if shape is not None:
        return shape

    shape = getattr(obj, "_shape", None)
    if shape is not None:
        return shape

    # FreeCAD document object / generic wrapper.
    shape = getattr(obj, "Shape", None)
    if shape is not None:
        return shape

    return obj


def _shape_is_null(shape: Any) -> bool:
    return shape is None or bool(getattr(shape, "isNull", lambda: False)())


def _shape_is_valid(shape: Any) -> bool:
    if _shape_is_null(shape):
        return False

    fn = getattr(shape, "isValid", None)
    if callable(fn):
        try:
            return bool(fn())
        except Exception:
            return False

    # If the object does not expose isValid(), do not invent a failure.
    return True


def _volume(shape: Any) -> float | None:
    try:
        value = getattr(shape, "Volume")
        return float(value)
    except Exception:
        pass

    fn = getattr(shape, "volume", None)
    if callable(fn):
        try:
            return float(fn())
        except Exception:
            pass

    return None


def _copy_shape(shape: Any) -> Any:
    fn = getattr(shape, "copy", None)
    if callable(fn):
        try:
            return fn()
        except Exception:
            return shape
    return shape


def _common_shape(a: Any, b: Any) -> Any:
    """
    Compute geometric intersection.

    Supports:
        Part.Shape.common(other)
        Part.Shape.common(...) through the project wrapper is handled
        by unwrapping before this function.
    """
    fn = getattr(a, "common", None)
    if not callable(fn):
        raise RuntimeError("FreeCAD shape does not expose common()")

    return fn(b)


def _fuse_shape(a: Any, b: Any) -> Any:
    fn = getattr(a, "fuse", None)
    if not callable(fn):
        raise RuntimeError("FreeCAD shape does not expose fuse()")
    return fn(b)


def _cut_shape(a: Any, b: Any) -> Any:
    fn = getattr(a, "cut", None)
    if not callable(fn):
        raise RuntimeError("FreeCAD shape does not expose cut()")
    return fn(b)


def _edges(shape: Any) -> list[Any]:
    return list(getattr(shape, "Edges", []) or [])


def _faces(shape: Any) -> list[Any]:
    return list(getattr(shape, "Faces", []) or [])


def _solids(shape: Any) -> list[Any]:
    return list(getattr(shape, "Solids", []) or [])


# ---------------------------------------------------------------------------
# Basic shape validation
# ---------------------------------------------------------------------------

def validate_shape(
    name: str,
    obj: Any,
    result: GeometryResult,
) -> Any | None:
    """Validate one produced shape and return its raw FreeCAD shape."""
    shape = _unwrap_shape(obj)

    if _shape_is_null(shape):
        result.error(name, "resulting shape is null/empty")
        return None

    if not _shape_is_valid(shape):
        result.error(
            name,
            "FreeCAD reports the resulting geometry as invalid",
        )
        return None

    volume = _volume(shape)

    if volume is not None and volume < -VOLUME_TOL:
        result.error(name, f"shape has negative volume ({volume:g})")

    return shape


# ---------------------------------------------------------------------------
# Boolean geometry checks
# ---------------------------------------------------------------------------

def validate_cut(
    where: str,
    target: Any,
    tool: Any,
    result: GeometryResult,
) -> None:
    try:
        common = _common_shape(target, tool)
    except Exception as exc:
        result.error(where, f"could not compute target/tool intersection: {exc}")
        return

    if _shape_is_null(common):
        result.error(
            where,
            "cut tool does not intersect target",
        )
        return

    common_volume = _volume(common)

    if common_volume is not None:
        if common_volume <= VOLUME_TOL:
            result.warning(
                where,
                "cut tool only touches target or has zero-volume intersection; "
                "no meaningful material may be removed",
            )

    try:
        cut_result = _cut_shape(target, tool)

        if _shape_is_null(cut_result):
            result.error(where, "FreeCAD returned a null result for the cut")
            return

        if not _shape_is_valid(cut_result):
            result.error(
                where,
                "FreeCAD produced an invalid shape after cut",
            )
    except Exception as exc:
        result.error(where, f"FreeCAD cut failed: {exc}")


def validate_common(
    where: str,
    a: Any,
    b: Any,
    result: GeometryResult,
) -> None:
    try:
        common = _common_shape(a, b)
    except Exception as exc:
        result.error(where, f"could not compute intersection: {exc}")
        return

    if _shape_is_null(common):
        result.error(where, "intersection is empty")

    volume = _volume(common)
    if volume is not None and volume <= VOLUME_TOL:
        result.warning(
            where,
            "intersection has zero/negligible volume",
        )


def validate_union(
    where: str,
    a: Any,
    b: Any,
    result: GeometryResult,
) -> None:
    try:
        fused = _fuse_shape(a, b)
    except Exception as exc:
        result.error(where, f"FreeCAD union/fuse failed: {exc}")
        return

    if _shape_is_null(fused):
        result.error(where, "FreeCAD returned a null result from union/fuse")
        return

    if not _shape_is_valid(fused):
        result.error(
            where,
            "FreeCAD produced an invalid shape after union/fuse",
        )


# ---------------------------------------------------------------------------
# Feature checks
# ---------------------------------------------------------------------------

def _try_make_fillet(shape: Any, radius: float, edge_list: Sequence[Any]) -> Any:
    fn = getattr(shape, "makeFillet", None)
    if callable(fn):
        return fn(radius, list(edge_list))

    try:
        import Part  # type: ignore
    except ImportError:
        Part = None

    if Part is not None:
        fn = getattr(Part, "makeFillet", None)
        if callable(fn):
            return fn(radius, list(edge_list), shape)

    raise RuntimeError(
        "no supported FreeCAD fillet API was found on this shape"
    )


def _try_make_chamfer(
    shape: Any,
    distance: float,
    edge_list: Sequence[Any],
) -> Any:
    fn = getattr(shape, "makeChamfer", None)
    if callable(fn):
        return fn(distance, list(edge_list))

    try:
        import Part  # type: ignore
    except ImportError:
        Part = None

    if Part is not None:
        fn = getattr(Part, "makeChamfer", None)
        if callable(fn):
            return fn(distance, list(edge_list), shape)

    raise RuntimeError(
        "no supported FreeCAD chamfer API was found on this shape"
    )


def _select_edges(shape: Any, edge_indices: Iterable[int] | None) -> list[Any]:
    all_edges = _edges(shape)

    if edge_indices is None:
        return all_edges

    selected = []
    for index in edge_indices:
        if not isinstance(index, int):
            raise TypeError(f"edge index must be an integer, got {index!r}")

        if index < 0 or index >= len(all_edges):
            raise IndexError(
                f"edge index {index} does not exist; "
                f"shape has {len(all_edges)} edge(s)"
            )

        selected.append(all_edges[index])

    return selected


def validate_fillet(
    where: str,
    target: Any,
    radius: float,
    edge_indices: Iterable[int] | None,
    result: GeometryResult,
) -> None:
    if radius <= 0:
        result.error(where, "fillet radius must be > 0")
        return

    test_shape = _copy_shape(target)
    
    try:
        edges = _select_edges(test_shape, edge_indices)
    except Exception as exc:
        result.error(where, f"invalid fillet edge selection: {exc}")
        return

    if not edges:
        result.error(where, "no edges were selected for fillet")
        return

    try:
        fillet_result = _try_make_fillet(test_shape, radius, edges)
    except Exception as exc:
        result.error(
            where,
            f"fillet radius/edge selection is geometrically invalid: {exc}",
        )
        return

    if _shape_is_null(fillet_result):
        result.error(where, "fillet returned a null shape")
        return

    if not _shape_is_valid(fillet_result):
        result.error(where, "FreeCAD produced an invalid shape after fillet")


def validate_chamfer(
    where: str,
    target: Any,
    distance: float,
    edge_indices: Iterable[int] | None,
    result: GeometryResult,
) -> None:
    if distance <= 0:
        result.error(where, "chamfer distance must be > 0")
        return

    test_shape = _copy_shape(target)
    
    try:
        edges = _select_edges(test_shape, edge_indices)
    except Exception as exc:
        result.error(where, f"invalid chamfer edge selection: {exc}")
        return

    if not edges:
        result.error(where, "no edges were selected for chamfer")
        return

    try:
        chamfer_result = _try_make_chamfer(test_shape, distance, edges)
    except Exception as exc:
        result.error(
            where,
            f"chamfer distance/edge selection is geometrically invalid: {exc}",
        )
        return

    if _shape_is_null(chamfer_result):
        result.error(where, "chamfer returned a null shape")
        return

    if not _shape_is_valid(chamfer_result):
        result.error(
            where,
            "FreeCAD produced an invalid shape after chamfer",
        )
# ---------------------------------------------------------------------------
# Main operation-level validator
# ---------------------------------------------------------------------------

def validate_geometry(
    data: Mapping[str, Any],
    shapes: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    result = GeometryResult()

    operations = data.get("operations")
    if not isinstance(operations, list):
        return (
            ["geometry: 'operations' must be a list"],
            [],
        )

    def get_shape(name: Any, where: str) -> Any | None:
        if not isinstance(name, str):
            result.error(where, f"shape reference must be a string, got {name!r}")
            return None

        if name not in shapes:
            result.error(
                where,
                f"built shape '{name}' is not available for geometry validation",
            )
            return None

        return validate_shape(name, shapes[name], result)

    for index, op in enumerate(operations):
        if not isinstance(op, dict):
            continue

        op_type = op.get("type")
        name = op.get("name")
        where = f"op[{index}] {op_type}"

        if isinstance(name, str) and name in shapes:
            validate_shape(name, shapes[name], result)

        if op_type in BOOLEAN_CUT_NAMES:
            target = get_shape(op.get("target"), where)
            tool = get_shape(op.get("other"), where)

            if target is not None and tool is not None:
                validate_cut(where, target, tool, result)

        elif op_type in BOOLEAN_COMMON_NAMES:
            target = get_shape(op.get("target"), where)
            tool = get_shape(op.get("other"), where)

            if target is not None and tool is not None:
                validate_common(where, target, tool, result)

        elif op_type in BOOLEAN_FUSE_NAMES:
            target = get_shape(op.get("target"), where)
            tool = get_shape(op.get("other"), where)

            if target is not None and tool is not None:
                validate_union(where, target, tool, result)

        elif op_type in FILLET_NAMES:
            target_name = op.get("target")
            target = get_shape(target_name, where)

            if target is not None:
                radius = op.get("radius")

                try:
                    radius = float(radius)
                except (TypeError, ValueError):
                    result.error(
                        where,
                        f"fillet radius must be numeric, got {radius!r}",
                    )
                    continue

                edge_indices = op.get("edges")
                if edge_indices is None and "edge" in op:
                    edge_indices = [op["edge"]]
                elif isinstance(edge_indices, int):
                    edge_indices = [edge_indices]

                validate_fillet(
                    where,
                    target,
                    radius,
                    edge_indices,
                    result,
                )

        elif op_type in CHAMFER_NAMES:
            target_name = op.get("target")
            target = get_shape(target_name, where)

            if target is not None:
                distance = op.get("distance")

                try:
                    distance = float(distance)
                except (TypeError, ValueError):
                    result.error(
                        where,
                        f"chamfer distance must be numeric, got {distance!r}",
                    )
                    continue

                edge_indices = op.get("edges")
                if edge_indices is None and "edge" in op:
                    edge_indices = [op["edge"]]
                elif isinstance(edge_indices, int):
                    edge_indices = [edge_indices]

                validate_chamfer(
                    where,
                    target,
                    distance,
                    edge_indices,
                    result,
                )

    return result.errors, result.warnings


# ---------------------------------------------------------------------------
# Small standalone API for your builder
# ---------------------------------------------------------------------------

def assert_geometry_ok(
    data: Mapping[str, Any],
    shapes: Mapping[str, Any],
) -> None:
    errors, warnings = validate_geometry(data, shapes)

    if errors:
        message = "Geometry validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        if warnings:
            message += "\nWarnings:\n" + "\n".join(
                f"  - {w}" for w in warnings
            )
        raise GeometryValidationError(message)


class GeometryValidationError(RuntimeError):
    pass