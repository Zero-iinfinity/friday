import FreeCAD as App
import Part 
from . import CADShape
class Primitives:
    @staticmethod
    def createBox( length, width, height, position=(0, 0, 0)):
        # Safely handle position as an App.Vector or a tuple/list
        v_pos = position if isinstance(position, App.Vector) else App.Vector(*position)
        return CADShape(Part.makeBox(length, width, height, v_pos))

    @staticmethod
    def createCylinder( radius, height, position=(0, 0, 0)):
        v_pos = position if isinstance(position, App.Vector) else App.Vector(*position)
        return CADShape(Part.makeCylinder(radius, height, v_pos))

    @staticmethod
    def createCone( r1, r2, height, position=(0, 0, 0)):
        v_pos = position if isinstance(position, App.Vector) else App.Vector(*position)
        return CADShape(Part.makeCone(r1, r2, height, v_pos))

    @staticmethod
    def createSphere( radius, position=(0, 0, 0)):
        v_pos = position if isinstance(position, App.Vector) else App.Vector(*position)
        return CADShape(Part.makeSphere(radius, v_pos))

    @staticmethod
    def createTorus( r1, r2, position=(0, 0, 0)):
        v_pos = position if isinstance(position, App.Vector) else App.Vector(*position)
        return CADShape(Part.makeTorus(r1, r2, v_pos))