from dataclasses import dataclass
from typing import *


__all__ = 'Vector2', 'Vector3', 'MeshName', 'Mesh'


class Vector(tuple):
    __slots__ = []

    def __add__(a, b: 'Vector') -> 'Vector':
        return type(a)([x+y for x, y in zip(a, b)])

    def __sub__(a, b: 'Vector') -> 'Vector':
        return type(a)([x-y for x, y in zip(a, b)])

    def __mul__(a, b: float) -> 'Vector':
        return type(a)([x*b for x in a])

    def __truediv__(a, b: float) -> 'Vector':
        return type(a)([x/b for x in a])

    def vmul(a, b: 'Vector') -> 'Vector':
        return type(a)([x*y for x, y in zip(a, b)])

    def vdiv(a, b: 'Vector') -> 'Vector':
        return type(a)([x/y for x, y in zip(a, b)])

    def dot(a, b: 'Vector') -> float:
        return sum(x*y for x, y in zip(a, b))


def get_bounds(verts):
        return [
            Vector(fn([v[i] for v in verts]) for i in range(len(verts[0])))
            for fn in (min, max)
        ]


Vector2 = Vector3 = Vector
MeshName = NewType('MeshName', str)


class Mesh:
    def __init__(self, name: MeshName):
        self.name = name
        self.vertices: List[Vector3] = []
        self.normals: List[Vector3] = []
        self.texcoords: List[Vector2] = []
        self.indices: List[int] = []
        self.morph_targets: Dict[str, 'Mesh'] = {}

    def clone(self) -> 'Mesh':
        m = type(self)(self.name)
        for n in 'vertices normals texcoords indices'.split():
            getattr(m, n)[:] = getattr(self, n)
        return m

    def add_vertex(self, v: Vector3, n: Vector3, t: Vector2) -> int:
        i = len(self.vertices)
        self.vertices.append(v)
        self.normals.append(n)
        self.texcoords.append(t)
        return i
        
    def add_triangle(self, i1, i2, i3):
        self.indices.extend((i1, i2, i3))

    def get_morph_target(self, name):
        if name not in self.morph_targets:
            self.morph_targets[name] = self.clone()
        return self.morph_targets[name]

    def iter_triangles(self):
        it = iter(self.indices)
        while 1:
            try:
                a = next(it)
            except StopIteration:
                return
            b = next(it)
            c = next(it)
            yield a, b, c

    def translate(self, offset: Vector3) -> 'Mesh':
        mesh = self.clone()
        mesh.vertices = [
            v + offset
            for v in mesh.vertices
        ]
        return mesh

    def transform(self, offset: Vector3, scale: float) -> 'Mesh':
        mesh = self.clone()
        mesh.vertices = [
            v * scale + offset
            for v in mesh.vertices
        ]
        return mesh

    def scale3(self, vf: Vector3) -> 'Mesh':
        mesh = self.clone()
        mesh.vertices = [
            v.vmul(vf)
            for v in mesh.vertices
        ]
        mesh.normals = [
            v.vmul(vf)
            for v in mesh.normals
        ]
        return mesh

    def remap_coordinates(self, i1: int, i2: int, i3: int) -> 'Mesh':
        def map_coords(a: List[Vector3]):
            a[:] = [
                Vector3((v[i1], v[i2], v[i3]))
                for v in a
            ]

        mesh = self.clone()
        map_coords(mesh.vertices)
        map_coords(mesh.normals)
        return mesh

    def save_for_ksp(self, base_path: str) -> None:
        import array
        import struct

        def write_array(a, typecode, ext, length=None):
            length = len(a) if length is None else length
            a = array.array(typecode, [
                x
                for v in a
                for x in v
            ])
            path = f'{base_path}.{ext}'
            with open(path, 'wb') as f:
                f.write(struct.pack('<L', length))
                a.tofile(f)

        write_array(self.vertices, 'f', 'vtx')
        write_array(self.texcoords, 'f', 'tex')

        if self.normals:
            write_array(self.normals, 'f', 'nml')

        idx = [self.indices]
        write_array(idx, 'L', 'idx', length=len(self.indices))
