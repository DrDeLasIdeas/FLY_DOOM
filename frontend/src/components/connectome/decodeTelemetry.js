export function base64ToBytes(b64) {
  if (!b64) return new Uint8Array(0);
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function toTypedArray(b64, Ctor) {
  const bytes = base64ToBytes(b64);
  return new Ctor(bytes.buffer, bytes.byteOffset, bytes.byteLength / Ctor.BYTES_PER_ELEMENT);
}

export function decodeTopology(asset) {
  return {
    positions: toTypedArray(asset.positions_b64, Float32Array),
    regions: toTypedArray(asset.regions_b64, Uint8Array),
    ghostPositions: toTypedArray(asset.ghost_positions_b64, Float32Array),
    ghostRegions: toTypedArray(asset.ghost_regions_b64, Uint8Array),
    visibleIdx: toTypedArray(asset.visible_idx_b64, Int32Array),
    edges: toTypedArray(asset.edges_b64, Int32Array),
    edgeSign: toTypedArray(asset.edge_sign_b64, Int8Array),
    edgeWeight: toTypedArray(asset.edge_weight_b64, Float32Array),
    regionNames: asset.region_names ?? [],
    regionCounts: asset.region_counts ?? [],
    numVisible: asset.num_visible ?? 0,
    numGhost: asset.num_ghost ?? 0,
    numNeurons: asset.num_neurons ?? 0,
    synapseStats: asset.synapse_stats ?? {},
    biophysics: asset.biophysics ?? {},
    meshes: (asset.meshes ?? []).map((mesh) => ({
      group: mesh.group,
      name: mesh.name,
      vertices: toTypedArray(mesh.vertices_b64, Float32Array),
      faces: toTypedArray(mesh.faces_b64, Uint32Array),
      centroid: mesh.centroid ?? [0, 0, 0],
    })),
  };
}

export function decodeSpikeBits(b64, count) {
  const bytes = base64ToBytes(b64);
  const bits = new Uint8Array(count);
  for (let i = 0; i < count; i += 1) {
    bits[i] = (bytes[i >> 3] >> (7 - (i & 7))) & 1;
  }
  return bits;
}
