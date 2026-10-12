import FreeCAD as App
import Part 


class SketchGeometry:
    """Mixin class to add geometry to a CADSketch."""
    
    def add_line(self, start, end, is_construction=False):
        v_start = start if isinstance(start, App.Vector) else App.Vector(*start)
        v_end = end if isinstance(end, App.Vector) else App.Vector(*end)
        
        # Use Part.LineSegment, NOT Part.makeLine
        line = Part.LineSegment(v_start, v_end)
        
        # Add to the sketch and return the integer ID for constraints
        return self._shape.addGeometry(line, is_construction)
    
    def add_circle(self, center, radius, is_construction=False):
        v_center = center if isinstance(center, App.Vector) else App.Vector(*center)
        
        # In Sketcher, the normal is always Z (0, 0, 1) relative to the sketch's local 2D plane.
        # The tilt of the sketch itself is handled by how it is attached to the 3D model.
        circle = Part.Circle(v_center, App.Vector(0, 0, 1), radius)
        
        return self._shape.addGeometry(circle, is_construction)


class Sketch:
    """Factory to generate new sketches."""
    
    @staticmethod
    def create(name="Sketch"):
        from . import CADSketch 
        # Ensure a document exists
        doc = App.ActiveDocument or App.newDocument()
        
        # Create the actual FreeCAD Sketch object
        raw_sketch = doc.addObject('Sketcher::SketchObject', name)
        
        # Wrap it in our master class
        return CADSketch(raw_sketch)