import FreeCAD as App
import Sketcher

START = 1
END = 2
CENTER = 3


class Constraint:
    def coincident(self, geo_a, pos_a, geo_b, pos_b):
        self._shape.addConstraint(Sketcher.Constraint('Coincident', geo_a, pos_a, geo_b, pos_b))
        return self

    def horizontal(self, geo):
        self._shape.addConstraint(Sketcher.Constraint('Horizontal', geo))
        return self

    def vertical(self, geo):
        self._shape.addConstraint(Sketcher.Constraint('Vertical', geo))
        return self

    def parallel(self, geo_a, geo_b):
        self._shape.addConstraint(Sketcher.Constraint('Parallel', geo_a, geo_b))
        return self

    def perpendicular(self, geo_a, geo_b):
        self._shape.addConstraint(Sketcher.Constraint('Perpendicular', geo_a, geo_b))
        return self

    def tangent(self, geo_a, geo_b):
        self._shape.addConstraint(Sketcher.Constraint('Tangent', geo_a, geo_b))
        return self

    def equal(self, geo_a, geo_b):
        self._shape.addConstraint(Sketcher.Constraint('Equal', geo_a, geo_b))
        return self

    def pointOnObject(self, point_geo, point_pos, target_geo):
        self._shape.addConstraint(Sketcher.Constraint('PointOnObject', point_geo, point_pos, target_geo))
        return self

    def symmetric(self, geo_a, pos_a, geo_b, pos_b, mirror_line):
        self._shape.addConstraint(Sketcher.Constraint('Symmetric', geo_a, pos_a, geo_b, pos_b, mirror_line))
        return self

    def block(self, geo):
        self._shape.addConstraint(Sketcher.Constraint('Block', geo))
        return self

    def distance(self, geo, length):
        self._shape.addConstraint(Sketcher.Constraint('Distance', geo, length))
        return self

    def distanceX(self, geo, pos, value):
        self._shape.addConstraint(Sketcher.Constraint('DistanceX', geo, pos, value))
        return self

    def distanceY(self, geo, pos, value):
        self._shape.addConstraint(Sketcher.Constraint('DistanceY', geo, pos, value))
        return self

    def radius(self, geo, value):
        self._shape.addConstraint(Sketcher.Constraint('Radius', geo, value))
        return self

    def diameter(self, geo, value):
        self._shape.addConstraint(Sketcher.Constraint('Diameter', geo, value))
        return self

    def angle(self, geo, angle_rad):
        self._shape.addConstraint(Sketcher.Constraint('Angle', geo, angle_rad))
        return self