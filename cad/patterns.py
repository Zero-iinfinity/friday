import FreeCAD as App

class Patterns:
    def linearPattern(self, count, dx=0, dy=0, dz=0):
        
        if count < 2:
            return self.__class__(self._shape.copy())
            
        res = self._shape.copy()
        for i in range(1, count):
            t = self._shape.copy()
            t.translate(App.Vector(dx * i, dy * i, dz * i))
            res = res.fuse(t)
        return self.__class__(res)

    def circularPattern(self, count, axis="z", center=(0, 0, 0), angle=360):
        if count < 2:
            return self.__class__(self._shape.copy())
        
        v_center = center if isinstance(center, App.Vector) else App.Vector(*center)
        
        
        if isinstance(axis, str):
            d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
            if axis.lower() not in d:
                raise ValueError("String axis must be 'x', 'y', or 'z'.")
            v_axis = App.Vector(*d[axis.lower()])
        else:
            v_axis = axis if isinstance(axis, App.Vector) else App.Vector(*axis)

        step = angle / count if angle == 360 else angle / (count - 1)
        res = self._shape.copy()
        for i in range(1, count):
            t = self._shape.copy()
            t.rotate(v_center, v_axis, step * i)
            res = res.fuse(t)
            
        return self.__class__(res)