import FreeCAD as App

class Transform:
    def translate(self, x=0, y=0, z=0):
        t = self._shape.copy()
        t.translate(App.Vector(x, y, z))
        return self.__class__(t)

    def rotate(self, angle, axis="z", center=(0, 0, 0)):
        
        v_center = center if isinstance(center, App.Vector) else App.Vector(*center)
        
        
        if isinstance(axis, str):
            d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
            if axis.lower() not in d:
                raise ValueError("String axis must be 'x', 'y', or 'z'.")
            v_axis = App.Vector(*d[axis.lower()])
        else:
            v_axis = axis if isinstance(axis, App.Vector) else App.Vector(*axis)
            
        r = self._shape.copy()
        r.rotate(v_center, v_axis, angle)
        return self.__class__(r)

    def scale(self, scaling_factor):
        s = self._shape.copy()
        s.scale(scaling_factor)
        return self.__class__(s)

    def mirror(self, plane="x", point=(0, 0, 0)):
        
        v_point = point if isinstance(point, App.Vector) else App.Vector(*point)
        
        
        if isinstance(plane, str):
            d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
            if plane.lower() not in d:
                raise ValueError("String plane must be 'x', 'y', or 'z'.")
            v_normal = App.Vector(*d[plane.lower()])
        else:
            v_normal = plane if isinstance(plane, App.Vector) else App.Vector(*plane)
            
        
        return self.__class__(self._shape.mirror(v_point, v_normal))