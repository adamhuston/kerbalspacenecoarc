#!/usr/bin/python3
"""Convert the Neco Arc full-body OBJ into a KSP head replacement.

Pipeline:
  1. load the OBJ (with group tracking, see obj_parser)
  2. keep only the head groups (head / hair / ears / eyes / pupils)
  3. recenter, auto-yaw so the face points +z, scale and offset
  4. write a three.js preview (viewer/data.js) and the KSP binary
     mesh files (.vtx/.tex/.nml/.idx)

Tune the constants below and re-run; refresh the viewer to eyeball the
orientation and proportions.
"""
import json
import math
import os
import shutil
from pathlib import Path

from data_types import Vector3, Vector2, Mesh, get_bounds
from obj_parser import load_obj_model


# ---------------------------------------------------------------------------
# configuration -- tweak these and re-run
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent

OBJ_PATH = REPO / 'neco-arc-melty-bloodtype-lumina' / 'source' / \
    'Neco_Arc_By_Johan_Hoof' / 'Neco_Arc_By_Johan_Hoof.obj'
TEXTURE_PATH = REPO / 'neco-arc-melty-bloodtype-lumina' / 'textures' / \
    'Neco_Arc_Texture.png'

# which OBJ groups make up the head. A group is kept if it contains ANY of
# these substrings (case-insensitive).
HEAD_GROUP_KEYWORDS = ['head']

# KSP mod asset layout. The mesh files and texture are staged here so the
# whole GameData/KerbalSpaceNecoArc tree can be merged into a KSP install.
# The C# side loads the mesh with LoadMesh("NecoArcHead") and the texture
# with LoadTexture(TEX_DIR + "neco_arc.png").
GAMEDATA = REPO / 'GameData' / 'KerbalSpaceNecoArc'
OUTPUT_DIR = GAMEDATA / 'Models'
OUTPUT_NAME = 'NecoArcHead'
TEXTURE_OUT_DIR = GAMEDATA / 'Textures'
TEXTURE_OUT_NAME = 'neco_arc.png'

# manual transform tuning (applied after auto-centering + auto-yaw)
# TARGET_HEIGHT can be overridden without editing this file via the
# NECO_TARGET_HEIGHT environment variable (used by deploy.ps1 -Height).
TARGET_HEIGHT = float(os.environ.get('NECO_TARGET_HEIGHT', 0.35))  # head y-extent in KSP mesh units (tune in-game)
EXTRA_YAW_DEG = 0.0     # extra spin about vertical axis
PITCH_DEG = 0.0         # tilt forward/back about x axis
# OFFSET shifts the head in final KSP mesh units (same scale as TARGET_HEIGHT).
# +y raises the head, +z pushes it forward, +x moves it right. Overridable
# via NECO_OFFSET_X/Y/Z env vars (used by deploy.ps1 -OffsetX/-OffsetY/-OffsetZ).
# NOTE: in-game positioning is now handled by the plugin, which auto-aligns the
# head to the stock kerbal head at load (see NecoArcConfig.AlignToStockHead) and
# then applies NecoArcConfig.MANUAL_OFFSET. A baked OFFSET here is cancelled by
# that re-centering, so keep it at 0 unless you only want to move the viewer
# preview / an un-aligned build.
OFFSET = Vector3([
    float(os.environ.get('NECO_OFFSET_X', 0.0)),
    float(os.environ.get('NECO_OFFSET_Y', 0.0)),
    float(os.environ.get('NECO_OFFSET_Z', 0.0)),
])
AUTO_FACE_FORWARD = True  # rotate so eyes point +z

# decimation: reduce the (very dense) head to a game-friendly poly count.
# TARGET_REDUCTION is the fraction of triangles to remove (0.25 -> keep 75%);
# lower it to preserve more detail. Overridable via the NECO_TARGET_REDUCTION
# environment variable (used by deploy.ps1 -Reduction).
DECIMATE = True
TARGET_REDUCTION = float(os.environ.get('NECO_TARGET_REDUCTION', 0.25))


# ---------------------------------------------------------------------------
# mesh helpers
# ---------------------------------------------------------------------------
def group_is_head(name):
    if name is None:
        return False
    low = name.lower()
    return any(k in low for k in HEAD_GROUP_KEYWORDS)


def extract_groups(mesh, predicate):
    """Return a new Mesh with only the triangles whose group matches."""
    out = Mesh(mesh.name)
    remap = {}
    has_normals = bool(mesh.normals)
    for tri_i, tri in enumerate(mesh.iter_triangles()):
        if not predicate(mesh.triangle_groups[tri_i]):
            continue
        new_tri = []
        for old in tri:
            if old not in remap:
                remap[old] = out.add_vertex(
                    mesh.vertices[old],
                    mesh.normals[old] if has_normals else Vector3([1, 1, 1]),
                    mesh.texcoords[old],
                )
            new_tri.append(remap[old])
        out.add_triangle(*new_tri)
    return out


def centroid(verts):
    n = len(verts)
    return Vector3([sum(v[i] for v in verts) / n for i in range(3)])


def rotate_y(mesh, theta):
    c, s = math.cos(theta), math.sin(theta)

    def rot(v):
        return Vector3([v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c])

    out = mesh.clone()
    out.vertices = [rot(v) for v in out.vertices]
    out.normals = [rot(v) for v in out.normals]
    return out


def rotate_x(mesh, theta):
    c, s = math.cos(theta), math.sin(theta)

    def rot(v):
        return Vector3([v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c])

    out = mesh.clone()
    out.vertices = [rot(v) for v in out.vertices]
    out.normals = [rot(v) for v in out.normals]
    return out


def face_forward_yaw(full_mesh, head_centroid):
    """Yaw (radians) needed to point the eyes toward +z."""
    eyes = extract_groups(full_mesh, lambda g: g and 'eye' in g.lower())
    if not eyes.vertices:
        return 0.0
    eye_c = centroid(eyes.vertices)
    fwd = eye_c - head_centroid
    # angle between forward (fx, fz) and +z, rotate by -angle to align to +z
    return -math.atan2(fwd[0], fwd[2])


def decimate_mesh(mesh, reduction):
    """Quadric-decimate the mesh, carrying UVs/normals via the collapse map.

    UV seams are left un-welded so the simplifier treats them as boundaries
    and preserves them; per-vertex UVs/normals are re-averaged onto the
    surviving vertices using the original->output index mapping.
    """
    import numpy as np
    import fast_simplification as fs

    points = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.indices, dtype=np.int32).reshape(-1, 3)

    _, out_faces, collapses = fs.simplify(
        points, faces, reduction, return_collapses=True)
    _, out_faces, mapping = fs.replay_simplification(points, faces, collapses)
    mapping = np.asarray(mapping)
    out_faces = np.asarray(out_faces)
    n_out = int(mapping.max()) + 1

    def gather(attr, dim):
        src = np.asarray(attr, dtype=np.float64).reshape(-1, dim)
        acc = np.zeros((n_out, dim))
        np.add.at(acc, mapping, src)
        counts = np.bincount(mapping, minlength=n_out).reshape(-1, 1)
        return acc / np.maximum(counts, 1)

    out = Mesh(mesh.name)
    out_pos = gather(mesh.vertices, 3)
    out_uv = gather(mesh.texcoords, 2)
    out_nm = gather(mesh.normals, 3) if mesh.normals else None
    if out_nm is not None:
        norms = np.linalg.norm(out_nm, axis=1, keepdims=True)
        out_nm = out_nm / np.maximum(norms, 1e-8)

    for i in range(n_out):
        out.add_vertex(
            Vector3(out_pos[i].tolist()),
            Vector3(out_nm[i].tolist()) if out_nm is not None
            else Vector3([1, 1, 1]),
            Vector2(out_uv[i].tolist()),
        )
    for a, b, c in out_faces:
        out.add_triangle(int(a), int(b), int(c))
    return out


# ---------------------------------------------------------------------------
# preview + export
# ---------------------------------------------------------------------------
def write_viewer_data(mesh, viewer_dir, texture_name):
    positions = [x for v in mesh.vertices for x in v]
    normals = [x for v in mesh.normals for x in v]
    uvs = [x for v in mesh.texcoords for x in v]
    code = f"""// auto-generated by neco_convert.py
function initModels(scene) {{
    var geom = new THREE.BufferGeometry();
    geom.addAttribute('position', new THREE.BufferAttribute(
        new Float32Array({json.dumps(positions)}), 3));
    geom.addAttribute('normal', new THREE.BufferAttribute(
        new Float32Array({json.dumps(normals)}), 3));
    geom.addAttribute('uv', new THREE.BufferAttribute(
        new Float32Array({json.dumps(uvs)}), 2));
    geom.setIndex(new THREE.BufferAttribute(
        new Uint32Array({json.dumps(mesh.indices)}), 1));

    var tex = new THREE.TextureLoader().load('{texture_name}');
    tex.flipY = true;
    var material = new THREE.MeshLambertMaterial({{ map: tex, color: 0xffffff }});
    scene.add(new THREE.Mesh(geom, material));
}}
"""
    (viewer_dir / 'data.js').write_text(code)


def main():
    print(f'loading {OBJ_PATH.name} ...')
    with OBJ_PATH.open() as f:
        full = load_obj_model(f)
    print(f'  {len(full.vertices)} verts, '
          f'{len(full.indices) // 3} triangles')
    print('  groups:', sorted({g for g in full.triangle_groups if g}))

    head = extract_groups(full, group_is_head)
    if not head.vertices:
        raise SystemExit('No head triangles matched HEAD_GROUP_KEYWORDS')
    print(f'head: {len(head.vertices)} verts, '
          f'{len(head.indices) // 3} triangles')

    if DECIMATE:
        head = decimate_mesh(head, TARGET_REDUCTION)
        print(f'decimated: {len(head.vertices)} verts, '
              f'{len(head.indices) // 3} triangles')

    # 1. recenter on head centroid (compute yaw first, from original coords)
    c = centroid(head.vertices)
    yaw = face_forward_yaw(full, c) if AUTO_FACE_FORWARD else 0.0
    head = head.translate(Vector3([-c[0], -c[1], -c[2]]))

    # 2. auto-yaw so the face looks +z
    if yaw:
        print(f'auto yaw: {math.degrees(yaw):.1f} deg')
        head = rotate_y(head, yaw)

    # 3. manual orientation tweaks
    if EXTRA_YAW_DEG:
        head = rotate_y(head, math.radians(EXTRA_YAW_DEG))
    if PITCH_DEG:
        head = rotate_x(head, math.radians(PITCH_DEG))

    # 4. scale to target height (manual OFFSET is applied separately below so
    #    the viewer preview can stay at offset 0)
    lo, hi = get_bounds(head.vertices)
    height = hi[1] - lo[1]
    scale = TARGET_HEIGHT / height if height else 1.0
    head = head.transform(offset=Vector3([0.0, 0.0, 0.0]), scale=scale)

    # preview: the raw (offset-0) head, so the viewer's offset sliders read the
    # absolute NECO_OFFSET instead of stacking on top of a baked-in offset.
    viewer_dir = HERE / 'viewer'
    shutil.copyfile(TEXTURE_PATH, viewer_dir / 'neco_texture.png')
    write_viewer_data(head, viewer_dir, 'neco_texture.png')
    print(f'wrote {viewer_dir / "data.js"} (open viewer/viewer.html)')

    # 5. bake the manual offset into the in-game mesh
    final = head.translate(OFFSET)
    lo, hi = get_bounds(final.vertices)
    print(f'scaled by {scale:.4f}; offset={tuple(OFFSET)}; '
          f'bounds min={tuple(round(x,3) for x in lo)} '
          f'max={tuple(round(x,3) for x in hi)}')

    # KSP binaries + texture, staged in GameData layout
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    final.save_for_ksp(str(OUTPUT_DIR / OUTPUT_NAME))
    print(f'wrote KSP mesh files to {OUTPUT_DIR / OUTPUT_NAME}.*')

    TEXTURE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEXTURE_PATH, TEXTURE_OUT_DIR / TEXTURE_OUT_NAME)
    print(f'wrote texture to {TEXTURE_OUT_DIR / TEXTURE_OUT_NAME}')


if __name__ == '__main__':
    main()
