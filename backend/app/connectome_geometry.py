"""Mallas anatómicas paramétricas para el visor 3D del conectoma.

Genera superficies suaves (sin dependencias externas) que aproximan el
neuropilo de *Drosophila melanogaster*: cápsulas retinianas, lóbulos ópticos,
cuerpo del hongo, complejo central, clusters MBON/DAN y fascículos descendentes.
Las mallas se entregan como vértices/índices listos para `BufferGeometry`.
"""
from __future__ import annotations

import numpy as np


def _ellipsoid(center, radii, segments: int = 24, rings: int = 16, dome: bool = False):
    """Elipsoide UV. Si `dome=True` solo genera el hemisferio superior."""
    center = np.asarray(center, dtype=np.float64)
    radii = np.asarray(radii, dtype=np.float64)
    phi_max = np.pi * 0.5 if dome else np.pi

    vertices = []
    for i in range(rings + 1):
        phi = phi_max * i / rings
        for j in range(segments):
            theta = 2.0 * np.pi * j / segments
            vertices.append(
                [
                    np.sin(phi) * np.cos(theta),
                    np.cos(phi),
                    np.sin(phi) * np.sin(theta),
                ]
            )
    vertices = np.asarray(vertices, dtype=np.float64) * radii + center

    faces = []
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + j
            d = (i + 1) * segments + (j + 1) % segments
            faces.append([a, c, b])
            faces.append([b, c, d])
    return vertices.astype(np.float32), np.asarray(faces, dtype=np.uint32)


def _retina_patch(sign: float, segments: int = 28, rings: int = 20):
    theta = np.linspace(-0.92, 0.92, segments + 1)
    phi = np.linspace(-0.84, 0.84, rings + 1)
    vertices = []
    for p in phi:
        for t in theta:
            vertices.append(
                [
                    sign * 1.55 + np.sin(t),
                    0.12 + np.sin(p),
                    2.35 + np.cos(t) * np.cos(p),
                ]
            )
    vertices = np.asarray(vertices, dtype=np.float64)

    faces = []
    row = segments + 1
    for i in range(rings):
        for j in range(segments):
            a = i * row + j
            b = a + 1
            c = (i + 1) * row + j
            d = c + 1
            faces.append([a, c, b])
            faces.append([b, c, d])
    return vertices.astype(np.float32), np.asarray(faces, dtype=np.uint32)


def _bezier(p0, p1, p2, samples: int = 16):
    t = np.linspace(0.0, 1.0, samples)[:, None]
    p0, p1, p2 = (np.asarray(p, dtype=np.float64) for p in (p0, p1, p2))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2


def _tube(points, radius: float, sides: int = 10):
    points = np.asarray(points, dtype=np.float64)
    n = len(points)
    tangents = np.zeros_like(points)
    tangents[1:-1] = points[2:] - points[:-2]
    tangents[0] = points[1] - points[0]
    tangents[-1] = points[-1] - points[-2]
    lengths = np.linalg.norm(tangents, axis=1, keepdims=True)
    tangents = tangents / np.maximum(lengths, 1e-8)

    reference = np.array([0.0, 0.0, 1.0])
    vertices = []
    for center, tangent in zip(points, tangents):
        ref = reference if abs(np.dot(tangent, reference)) < 0.9 else np.array([0.0, 1.0, 0.0])
        normal = np.cross(tangent, ref)
        normal /= max(np.linalg.norm(normal), 1e-8)
        binormal = np.cross(tangent, normal)
        for k in range(sides):
            angle = 2.0 * np.pi * k / sides
            vertices.append(center + radius * (np.cos(angle) * normal + np.sin(angle) * binormal))
    vertices = np.asarray(vertices, dtype=np.float64)

    faces = []
    for i in range(n - 1):
        for k in range(sides):
            a = i * sides + k
            b = i * sides + (k + 1) % sides
            c = (i + 1) * sides + k
            d = (i + 1) * sides + (k + 1) % sides
            faces.append([a, c, b])
            faces.append([b, c, d])
    return vertices.astype(np.float32), np.asarray(faces, dtype=np.uint32)


def _merge(parts):
    vertices = []
    faces = []
    offset = 0
    for part_vertices, part_faces in parts:
        vertices.append(part_vertices)
        faces.append(part_faces + offset)
        offset += len(part_vertices)
    return np.vstack(vertices), np.vstack(faces)


def build_region_meshes(region_names) -> list[dict]:
    """Devuelve una malla suave por cada grupo anatómico."""
    meshes: list[dict] = []

    def add(group: int, parts):
        vertices, faces = _merge(parts)
        meshes.append(
            {
                "group": int(group),
                "name": str(region_names[group]),
                "vertices": vertices.astype(np.float32),
                "faces": faces.astype(np.uint32),
                "centroid": vertices.mean(axis=0).astype(np.float32),
            }
        )

    add(0, [_retina_patch(-1.0)])
    add(1, [_retina_patch(1.0)])

    add(2, [_ellipsoid((-1.72, -0.10, 1.05), (0.72, 0.58, 0.88))])
    add(3, [_ellipsoid((1.72, -0.10, 1.05), (0.72, 0.58, 0.88))])

    peduncle = _bezier((-0.05, 0.30, -0.30), (0.0, -0.35, 0.15), (0.0, -0.55, 0.45))
    add(
        4,
        [
            _ellipsoid((0.0, 0.75, -0.45), (0.85, 0.55, 0.80), dome=True),
            _tube(peduncle, 0.10),
            _tube(_bezier((-0.15, -0.50, 0.35), (-0.35, -0.40, 0.80), (-0.55, -0.25, 1.25)), 0.085),
            _tube(_bezier((0.15, -0.50, 0.35), (0.35, -0.40, 0.80), (0.55, -0.25, 1.25)), 0.085),
        ],
    )

    add(
        5,
        [
            _ellipsoid((0.0, 0.0, -0.10), (0.60, 0.38, 0.50)),
            _ellipsoid((-0.85, -0.15, 0.25), (0.20, 0.16, 0.20)),
            _ellipsoid((0.85, -0.15, 0.25), (0.20, 0.16, 0.20)),
        ],
    )

    mbon_centers = [
        (-0.35, -0.45, 0.15),
        (0.35, -0.45, 0.15),
        (-0.55, -0.25, 0.90),
        (0.55, -0.25, 0.90),
    ]
    add(6, [_ellipsoid(center, (0.14, 0.14, 0.14), segments=16, rings=10) for center in mbon_centers])

    dan_centers = [
        (-0.25, -0.35, 0.20),
        (0.25, -0.35, 0.20),
        (-0.15, 0.25, -0.35),
        (0.15, 0.25, -0.35),
    ]
    add(7, [_ellipsoid(center, (0.11, 0.11, 0.11), segments=14, rings=9) for center in dan_centers])

    dn_fascicles = [
        [(-0.35, 0.15, 0.05), (-0.35, -0.40, 0.02), (-0.35, -0.95, 0.00)],
        [(0.35, 0.15, 0.05), (0.35, -0.40, 0.02), (0.35, -0.95, 0.00)],
        [(0.00, 0.10, -0.15), (0.00, -0.50, -0.15), (0.00, -1.05, -0.15)],
        [(0.00, 0.20, 0.45), (0.00, -0.40, 0.45), (0.00, -1.15, 0.45)],
    ]
    for offset, group in enumerate((8, 9, 10, 11)):
        add(group, [_tube(dn_fascicles[offset], 0.045, sides=8)])

    return meshes
