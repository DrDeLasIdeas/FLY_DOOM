#!/usr/bin/env python3
"""Genera el artefacto .npz del conectoma bio-inspirado en FlyWire v783.

La topología sináptica (pre_idx, post_idx, weights) se mantiene idéntica a la
versión entrenada para no invalidar `data/motor_policy.pt`. Solo se enriquece
`coords_3d` con anatomía paramétrica de Drosophila y se añaden metadatos de
región y un subconjunto visible para el render 3D en vivo.
"""
import os
import numpy as np

NUM_NEURONS = 20000

REGION_NAMES = np.array(
    [
        "Retina Izquierda",
        "Retina Derecha",
        "Lóbulo Óptico Izquierdo",
        "Lóbulo Óptico Derecho",
        "Cuerpo del Hongo (KC)",
        "Complejo Central",
        "MBON (Salida del Hongo)",
        "DAN (Dopamina)",
        "DNp20 Izquierda",
        "DNp20 Derecha",
        "DN Movimiento",
        "DNp09 Ataque",
    ]
)

VISIBLE_TARGETS = {
    0: 450,
    1: 450,
    2: 350,
    3: 350,
    4: 900,
    5: 596,
    6: 500,
    7: 300,
    8: 50,
    9: 50,
    10: 50,
    11: 50,
}

MAX_DISPLAY_EDGES = 30000


def _ellipsoid_shell(rng, n, center, radii, thickness=0.12):
    direction = rng.normal(size=(n, 3))
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    radius = 1.0 + rng.normal(0.0, thickness, size=(n, 1))
    return np.asarray(center) + direction * np.asarray(radii) * radius


def _cluster(rng, n, center, sigma):
    return np.asarray(center) + rng.normal(0.0, sigma, size=(n, 3))


def _retina_coords(rng):
    idx = np.arange(4096)
    row = idx // 64
    col = idx % 64
    left = col < 32
    col_local = np.where(left, col, col - 32)
    theta = (col_local / 31.0 * 2.0 - 1.0) * 0.85
    phi = (row / 63.0 * 2.0 - 1.0) * 0.78
    radius = 1.0
    coords = np.zeros((4096, 3), dtype=np.float64)
    coords[:, 0] = np.where(left, -1.55, 1.55) + radius * np.sin(theta)
    coords[:, 1] = 0.12 + radius * np.sin(phi)
    coords[:, 2] = 2.35 + radius * np.cos(theta) * np.cos(phi)
    return coords + rng.normal(0.0, 0.012, coords.shape)


def _optic_coords(rng):
    left = _ellipsoid_shell(rng, 2048, (-1.72, -0.10, 1.05), (0.72, 0.58, 0.88), 0.10)
    right = _ellipsoid_shell(rng, 2048, (1.72, -0.10, 1.05), (0.72, 0.58, 0.88), 0.10)
    return np.vstack([left, right])


def _mushroom_body_coords(rng):
    calyx_dir = rng.normal(size=(4915, 3))
    calyx_dir /= np.linalg.norm(calyx_dir, axis=1, keepdims=True)
    calyx_dir[:, 1] = np.abs(calyx_dir[:, 1])
    calyx = np.asarray((0.0, 0.75, -0.45)) + calyx_dir * np.asarray((0.85, 0.55, 0.80))
    calyx += rng.normal(0.0, 0.015, calyx.shape)

    t = rng.uniform(0.0, 1.0, size=(1229, 1))
    p0 = np.asarray((-0.05, 0.30, -0.30))
    p1 = np.asarray((0.0, -0.35, 0.15))
    p2 = np.asarray((0.0, -0.55, 0.45))
    peduncle = (
        (1 - t) ** 2 * p0
        + 2 * (1 - t) * t * p1
        + t**2 * p2
        + rng.normal(0.0, 0.11, size=(1229, 3))
    )

    def lobe(origin, tip):
        t_lobe = rng.uniform(0.0, 1.0, size=(1024, 1))
        return (
            (1 - t_lobe) * np.asarray(origin)
            + t_lobe * np.asarray(tip)
            + rng.normal(0.0, 0.14, size=(1024, 3))
        )

    lobe_left = lobe((-0.15, -0.50, 0.35), (-0.55, -0.25, 1.25))
    lobe_right = lobe((0.15, -0.50, 0.35), (0.55, -0.25, 1.25))
    return np.vstack([calyx, peduncle, lobe_left, lobe_right])


def _central_complex_coords(rng):
    cc = _ellipsoid_shell(rng, 1900, (0.0, 0.0, -0.10), (0.60, 0.38, 0.50), 0.10)
    lh_left = _cluster(rng, 358, (-0.85, -0.15, 0.25), (0.16, 0.13, 0.16))
    lh_right = _cluster(rng, 358, (0.85, -0.15, 0.25), (0.16, 0.13, 0.16))
    return np.vstack([cc, lh_left, lh_right])


def _mbon_coords(rng):
    return np.vstack(
        [
            _cluster(rng, 130, (-0.35, -0.45, 0.15), (0.10, 0.10, 0.10)),
            _cluster(rng, 130, (0.35, -0.45, 0.15), (0.10, 0.10, 0.10)),
            _cluster(rng, 120, (-0.55, -0.25, 0.90), (0.11, 0.10, 0.12)),
            _cluster(rng, 120, (0.55, -0.25, 0.90), (0.11, 0.10, 0.12)),
        ]
    )


def _dan_coords(rng):
    return np.vstack(
        [
            _cluster(rng, 90, (-0.25, -0.35, 0.20), (0.10, 0.10, 0.10)),
            _cluster(rng, 90, (0.25, -0.35, 0.20), (0.10, 0.10, 0.10)),
            _cluster(rng, 60, (-0.15, 0.25, -0.35), (0.08, 0.09, 0.09)),
            _cluster(rng, 60, (0.15, 0.25, -0.35), (0.08, 0.09, 0.09)),
        ]
    )


def _dn_coords(rng):
    sigma = (0.06, 0.28, 0.09)
    return np.vstack(
        [
            _cluster(rng, 50, (-0.35, -0.85, 0.00), sigma),
            _cluster(rng, 50, (0.35, -0.85, 0.00), sigma),
            _cluster(rng, 50, (0.00, -1.00, -0.15), sigma),
            _cluster(rng, 50, (0.00, -1.10, 0.45), sigma),
        ]
    )


def _build_regions(num_neurons):
    regions = np.zeros(num_neurons, dtype=np.uint8)
    col = np.arange(4096) % 64
    regions[0:4096] = np.where(col < 32, 0, 1)
    regions[4096:6144] = 2
    regions[6144:8192] = 3
    regions[8192:16384] = 4
    regions[16384:19000] = 5
    regions[19000:19500] = 6
    regions[19500:19800] = 7
    regions[19800:19850] = 8
    regions[19850:19900] = 9
    regions[19900:19950] = 10
    regions[19950:20000] = 11
    return regions


def _build_coords(rng):
    return np.vstack(
        [
            _retina_coords(rng),
            _optic_coords(rng),
            _mushroom_body_coords(rng),
            _central_complex_coords(rng),
            _mbon_coords(rng),
            _dan_coords(rng),
            _dn_coords(rng),
        ]
    ).astype(np.float32)


def _build_visible_idx(regions, rng):
    selected = []
    for group, target in VISIBLE_TARGETS.items():
        candidates = np.flatnonzero(regions == group)
        if target >= len(candidates):
            selected.append(candidates)
        else:
            selected.append(rng.choice(candidates, size=target, replace=False))
    return np.sort(np.concatenate(selected)).astype(np.int32)


def _build_display_edges(pre_idx, post_idx, weights, visible_idx, rng):
    visible_mask = np.zeros(NUM_NEURONS, dtype=bool)
    visible_mask[visible_idx] = True
    selected = np.flatnonzero(visible_mask[pre_idx] & visible_mask[post_idx])
    if len(selected) > MAX_DISPLAY_EDGES:
        selected = rng.choice(selected, size=MAX_DISPLAY_EDGES, replace=False)
        selected.sort()
    display_edges = np.stack([pre_idx[selected], post_idx[selected]], axis=1).astype(np.int32)
    edge_sign = np.sign(weights[selected]).astype(np.int8)
    edge_weight = weights[selected].astype(np.float32)
    return display_edges, edge_sign, edge_weight


def build_connectome_artifact(
    output_path: str = "data/flywire_subconnectome.npz",
    num_neurons: int = NUM_NEURONS,
):
    if num_neurons != NUM_NEURONS:
        raise ValueError(f"El layout anatómico está fijado a {NUM_NEURONS} neuronas.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"[Connectome Builder] Generando topología FlyWire ({num_neurons} neuronas)...")

    # Bloque sináptico congelado: mismo RNG y mismo orden que la versión entrenada.
    rng = np.random.default_rng(42)

    s1 = rng.integers(0, 4096, size=120000)
    t1 = rng.integers(4096, 8192, size=120000)
    w1 = rng.uniform(0.4, 1.5, size=120000)

    s2 = rng.integers(4096, 8192, size=180000)
    t2 = rng.integers(8192, 19000, size=180000)
    w2 = rng.uniform(-0.8, 1.4, size=180000)

    s3 = rng.integers(8192, 19000, size=180000)
    t3 = rng.integers(8192, 19000, size=180000)
    w3 = rng.uniform(-1.0, 1.0, size=180000)

    s4 = rng.integers(8192, 16384, size=70000)
    t4 = rng.integers(19000, 19500, size=70000)
    w4 = rng.uniform(0.1, 0.9, size=70000)

    s5 = rng.integers(16384, 19500, size=50000)
    t5 = rng.integers(19800, 20000, size=50000)
    w5 = rng.uniform(-0.6, 1.6, size=50000)

    pre_idx = np.concatenate([s1, s2, s3, s4, s5]).astype(np.int32)
    post_idx = np.concatenate([t1, t2, t3, t4, t5]).astype(np.int32)
    weights = np.concatenate([w1, w2, w3, w4, w5]).astype(np.float32)

    geometry_rng = np.random.default_rng(7)
    selection_rng = np.random.default_rng(2024)

    coords_3d = _build_coords(geometry_rng)
    regions = _build_regions(num_neurons)
    visible_idx = _build_visible_idx(regions, selection_rng)
    display_edges, edge_sign, edge_weight = _build_display_edges(
        pre_idx, post_idx, weights, visible_idx, selection_rng
    )

    np.savez_compressed(
        output_path,
        num_neurons=num_neurons,
        pre_idx=pre_idx,
        post_idx=post_idx,
        weights=weights,
        coords_3d=coords_3d,
        regions=regions,
        region_names=REGION_NAMES,
        visible_idx=visible_idx,
        display_edges=display_edges,
        edge_sign=edge_sign,
        edge_weight=edge_weight,
    )
    print(
        f"[Connectome Builder] {len(visible_idx)} neuronas visibles, "
        f"{len(display_edges)} sinapsis visibles → {output_path}"
    )


if __name__ == "__main__":
    build_connectome_artifact()
