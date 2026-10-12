import FreeCAD as App
import Part 

class Features:
    def fillet(self, radius, edges=None):
        all_edges = self._shape.Edges
        if edges is not None:
            if isinstance(edges, int):
                edges = [edges]
            chosen = []
            for i in edges:
                if 0 <= i < len(all_edges):
                    chosen.append(all_edges[i])
                else:
                    raise IndexError(f"Edge index {i} is out of range. Shape only has {len(all_edges)} edges.")
        else:
            chosen = all_edges
            
        return self.__class__(self._shape.makeFillet(radius, chosen))

    def chamfer(self, distance, edges=None):
        all_edges = self._shape.Edges
        if edges is not None:
            if isinstance(edges, int):
                edges = [edges]
                
            chosen = []
            for i in edges:
                if 0 <= i < len(all_edges):
                    chosen.append(all_edges[i])
                else:
                    raise IndexError(f"Edge index {i} is out of range. Shape only has {len(all_edges)} edges.")
        else:
            chosen = all_edges
            
        return self.__class__(self._shape.makeChamfer(distance, chosen))

    
    def hole(self, radius, position, depth=None):
        
        v_position = position if isinstance(position, App.Vector) else App.Vector(*position)
        
        if depth is None:
            
            depth = self._shape.BoundBox.ZMax - v_position.z
            
        cyl = Part.makeCylinder(radius, depth, v_position)
        res = self._shape.cut(cyl)
        return self.__class__(res)