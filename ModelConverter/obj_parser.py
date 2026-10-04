from data_types import *


def load_obj_model(f):
    vertices = []
    texcoords = []
    normals = []
    faces = []
    face_groups = []
    current_group = None

    for s in f:
        t = s.split()
        if len(t) < 1:
            continue
        elif t[0] == 'v':
            vertices.append(Vector3([float(x) for x in t[1:4]]))
        elif t[0] == 'vt':
            texcoords.append(Vector2([float(x) for x in t[1:3]]))
        elif t[0] == 'vn':
            normals.append(Vector3([float(x) for x in t[1:4]]))
        elif t[0] in ('g', 'o'):
            current_group = ' '.join(t[1:])
        elif t[0] == 'f':
            faces.append(tuple(
                tuple(int(y) - 1 if y else None for y in x.split('/'))
                for x in t[1:]
            ))
            face_groups.append(current_group)

    m = Mesh('obj')
    # group name for each triangle, aligned with m.iter_triangles()
    m.triangle_groups = []

    index_map = {}
    for face, group in zip(faces, face_groups):
        inds = []
        for ind in face:
            vi = ind[0]
            ti = ind[1] if len(ind) > 1 else None
            ni = ind[2] if len(ind) > 2 else None
            key = (vi, ti)
            if key not in index_map:
                i = m.add_vertex(
                    vertices[vi],
                    normals[ni] if ni is not None else Vector3([1, 1, 1]),
                    texcoords[ti] if ti is not None else Vector2([0, 0]),
                )
                index_map[key] = i
            else:
                i = index_map[key]
            inds.append(i)

        # fan triangulation: handles triangles, quads and n-gons
        for k in range(1, len(inds) - 1):
            m.add_triangle(inds[0], inds[k], inds[k + 1])
            m.triangle_groups.append(group)

    return m