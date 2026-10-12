import FreeCAD as App
from praser import json_loader
from cad import Primitives, Sketch, Feature3D
from validator.schema import validate
from validator.geometry import validate_geometry

FACTORIES = {
    "create_box": Primitives.createBox,
    "create_cylinder": Primitives.createCylinder,
    "create_sphere": Primitives.createSphere,
    "create_cone": Primitives.createCone,
    "create_torus": Primitives.createTorus,
    "create_sketch": Sketch.create,
    "extrude": Feature3D.extrude,
    "revolve": Feature3D.revolve,
    "sweep": Feature3D.sweep,
    "loft": Feature3D.loft
}

def build(path):
    data = json_loader.load(path)

    # ==========================================
    # 1. JSON VALIDATOR
    # ==========================================
    schema_errors, schema_warnings = validate(data)
    
    if schema_warnings:
        for w in schema_warnings:
            print(f"JSON WARNING: {w}")
            
    if schema_errors:
        print("--- JSON VALIDATION FAILED ---")
        for e in schema_errors:
            print(f"  - {e}")
        raise ValueError("JSON Validation failed. See logs above.")

    # ==========================================
    # 2. STAGING BUILDER (Generate shapes in memory)
    # ==========================================
    operations = data.get("operations", [])
    shapes = {}
    
    for op in operations:
        op_type = op.get("type")
        name = op.get("name")
        kwargs = {k: v for k, v in op.items() if k not in ("type", "name")}
        
        for key, value in kwargs.items():
            if isinstance(value, str) and value in shapes:
                kwargs[key] = shapes[value]
            elif isinstance(value, list):
                kwargs[key] = [shapes[v] if (isinstance(v, str) and v in shapes) else v for v in value]

        try:
            if op_type in FACTORIES:
                func = FACTORIES[op_type]
                shapes[name] = func(**kwargs)
            else:
                target_obj = kwargs.pop("target", None)
                if not target_obj:
                    print(f"BUILD ERROR: Target missing or not found for operation '{op_type}'.")
                    continue
                    
                if hasattr(target_obj, op_type):
                    method_to_call = getattr(target_obj, op_type)
                    shapes[name] = method_to_call(**kwargs)
                else:
                    print(f"BUILD WARNING: Operation '{op_type}' is not supported on {type(target_obj).__name__}.")
        except Exception as e:
            # Catch underlying FreeCAD kernel crashes during staging
            raise ValueError(f"FreeCAD kernel failed to build operation '{name}' ({op_type}): {e}")

    if App.ActiveDocument:
        App.ActiveDocument.recompute()

    # ==========================================
    # 3. GEOMETRY VALIDATOR
    # ==========================================
    geo_errors, geo_warnings = validate_geometry(data, shapes)
    
    if geo_warnings:
        for w in geo_warnings:
            print(f"GEOMETRY WARNING: {w}")
            
    if geo_errors:
        print("--- GEOMETRY VALIDATION FAILED ---")
        for e in geo_errors:
            print(f"  - {e}")
        raise ValueError("Geometry Validation failed. See logs above.")

    # ==========================================
    # 4. FINAL BUILDER OUTPUT
    # ==========================================
    return shapes