import FreeCAD as App
import Part

class Boolean:
    def _get_shape(self, obj):
        """
        Helper method to safely extract the shape.
        If 'obj' has a '_shape' attribute (like your custom classes), it returns that.
        If not, it assumes 'obj' is already a raw FreeCAD shape.
        """
        return getattr(obj, '_shape', obj)

    def union(self, other):
        other_shape = self._get_shape(other)
        return self.__class__(self._shape.fuse(other_shape))

    def cut(self, other):
        other_shape = self._get_shape(other)
        return self.__class__(self._shape.cut(other_shape))

    def intersection(self, other):
        other_shape = self._get_shape(other)
        return self.__class__(self._shape.common(other_shape))