import React, { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Billboard, OrbitControls } from "@react-three/drei";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";
import { base64ToBytes, decodeSpikeBits } from "./decodeTelemetry.js";
import { REGION_COLORS, REGION_HEX, SYNAPSE_COLORS } from "./palette.js";

const VIEW_PRESETS = {
  mosca: { position: [4.6, 3.0, 6.2], target: [0, -0.1, 0.3], rotate: true, explode: 0 },
  frontal: { position: [0, 0.4, 8.0], target: [0, 0.0, 0.4], rotate: false, explode: 0 },
  explotada: { position: [5.8, 4.2, 6.4], target: [0, -0.2, 0.3], rotate: true, explode: 1.2 },
  sagital: { position: [0.2, 0.3, 7.6], target: [0, 0.0, 0.2], rotate: false, explode: 0 },
};

const CLIP_DISABLED = -1e6;

const POINT_VERTEX = `
attribute vec3 aColor;
attribute float aIndex;
attribute float aAttack;

uniform sampler2D uSpikeTex;
uniform sampler2D uVoltTex;
uniform float uCount;
uniform float uTime;
uniform float uSize;
uniform float uAttack;
uniform float uExplode;
uniform vec3 uCenter;

varying vec3 vColor;
varying float vGlow;
varying vec3 vWorldPos;

void main() {
  vec2 uv = vec2((aIndex + 0.5) / uCount, 0.5);
  float spikeTime = texture2D(uSpikeTex, uv).r;
  float volt = texture2D(uVoltTex, uv).r;

  float age = uTime - spikeTime;
  float glow = age >= 0.0 ? exp(-age * 4.5) : 0.0;
  float attackGlow = uAttack * aAttack;

  vec3 voltColor = mix(vec3(0.259, 0.522, 0.957), vec3(0.204, 0.659, 0.325), smoothstep(0.0, 0.45, volt));
  voltColor = mix(voltColor, vec3(0.984, 0.737, 0.020), smoothstep(0.45, 0.78, volt));
  voltColor = mix(voltColor, vec3(0.918, 0.263, 0.208), smoothstep(0.78, 1.0, volt));

  vec3 base = mix(aColor * (0.35 + 0.65 * volt), voltColor, 0.55);
  vec3 hot = mix(base, vec3(0.918, 0.263, 0.208), clamp(attackGlow, 0.0, 1.0));
  vColor = mix(hot, vec3(1.0, 1.0, 1.0), glow * 0.85);
  vGlow = glow;

  vec3 expanded = position + normalize(position - uCenter + 0.0001) * uExplode;
  vec4 world = modelMatrix * vec4(expanded, 1.0);
  vWorldPos = world.xyz;
  vec4 mv = viewMatrix * world;
  float perspective = 300.0 / max(0.1, -mv.z);
  float size = uSize * perspective * (0.8 + 0.6 * volt) + 6.0 * glow + 9.0 * attackGlow;
  gl_PointSize = clamp(size, 1.0, 26.0);
  gl_Position = projectionMatrix * mv;
}
`;

const POINT_FRAGMENT = `
uniform vec3 uClipNormal;
uniform float uClipConstant;

varying vec3 vColor;
varying float vGlow;
varying vec3 vWorldPos;

void main() {
  if (dot(uClipNormal, vWorldPos) + uClipConstant > 0.0) discard;
  vec2 coord = gl_PointCoord - 0.5;
  float dist = length(coord);
  if (dist > 0.5) discard;
  float alpha = smoothstep(0.5, 0.06, dist);
  gl_FragColor = vec4(vColor, alpha * (0.72 + 0.28 * vGlow));
}
`;

const GHOST_VERTEX = `
attribute vec3 aColor;
attribute float aRegion;
attribute float aIndex;

uniform sampler2D uRegionTex;
uniform float uTime;
uniform float uSize;
uniform float uExplode;
uniform vec3 uCenter;

varying vec3 vColor;
varying float vAlpha;
varying vec3 vWorldPos;

void main() {
  float activity = texture2D(uRegionTex, vec2((aRegion + 0.5) / 12.0, 0.5)).r;
  vColor = aColor * (0.4 + 0.9 * activity);
  vAlpha = 0.05 + 0.13 * activity;

  vec3 expanded = position + normalize(position - uCenter + 0.0001) * uExplode;
  vec4 world = modelMatrix * vec4(expanded, 1.0);
  vWorldPos = world.xyz;
  vec4 mv = viewMatrix * world;
  float perspective = 300.0 / max(0.1, -mv.z);
  float twinkle = 0.9 + 0.1 * sin(uTime * 0.6 + aIndex * 0.37);
  gl_PointSize = clamp(uSize * perspective * twinkle, 1.0, 8.0);
  gl_Position = projectionMatrix * mv;
}
`;

const GHOST_FRAGMENT = `
uniform vec3 uClipNormal;
uniform float uClipConstant;

varying vec3 vColor;
varying float vAlpha;
varying vec3 vWorldPos;

void main() {
  if (dot(uClipNormal, vWorldPos) + uClipConstant > 0.0) discard;
  vec2 coord = gl_PointCoord - 0.5;
  float dist = length(coord);
  if (dist > 0.5) discard;
  gl_FragColor = vec4(vColor, vAlpha * smoothstep(0.5, 0.1, dist));
}
`;

const EDGE_VERTEX = `
attribute float aPre;
attribute float aT;
attribute vec3 aColor;
attribute float aWeight;
attribute float aKind;

uniform sampler2D uSpikeTex;
uniform float uCount;
uniform float uExplode;
uniform vec3 uCenter;

varying vec3 vColor;
varying float vT;
varying float vWeight;
varying float vSpikeTime;
varying float vKind;
varying vec3 vWorldPos;

void main() {
  vec2 uv = vec2((aPre + 0.5) / uCount, 0.5);
  vSpikeTime = texture2D(uSpikeTex, uv).r;
  vColor = aColor;
  vT = aT;
  vWeight = aWeight;
  vKind = aKind;

  vec3 expanded = position + normalize(position - uCenter + 0.0001) * uExplode;
  vec4 world = modelMatrix * vec4(expanded, 1.0);
  vWorldPos = world.xyz;
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

const EDGE_FRAGMENT = `
uniform float uTime;
uniform float uSpeed;
uniform float uFilter;
uniform float uMinWeight;
uniform vec3 uClipNormal;
uniform float uClipConstant;

varying vec3 vColor;
varying float vT;
varying float vWeight;
varying float vSpikeTime;
varying float vKind;
varying vec3 vWorldPos;

void main() {
  if (dot(uClipNormal, vWorldPos) + uClipConstant > 0.0) discard;
  if (uMinWeight > 0.0 && vWeight < uMinWeight) discard;
  if (uFilter > 0.5) {
    if (uFilter < 1.5 && vKind > 0.5) discard;
    else if (uFilter < 2.5 && abs(vKind - 1.0) > 0.5) discard;
    else if (uFilter < 3.5 && abs(vKind - 2.0) > 0.5) discard;
  }

  float age = uTime - vSpikeTime;
  float travel = age * uSpeed;
  float delta = abs(vT - travel);
  float pulse = (age >= 0.0 && travel <= 1.35) ? exp(-delta * delta * 260.0) : 0.0;

  vec3 color = vColor * (0.10 + 0.18 * vWeight + pulse * 1.4);
  float alpha = 0.045 + pulse * 0.72;
  gl_FragColor = vec4(color, alpha);
}
`;

const MESH_VERTEX = `
uniform float uExplode;
uniform vec3 uCenter;

varying vec3 vWorldPos;
varying vec3 vNormalW;

void main() {
  vec3 expanded = position + normalize(position - uCenter + 0.0001) * uExplode;
  vec4 world = modelMatrix * vec4(expanded, 1.0);
  vWorldPos = world.xyz;
  vNormalW = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

const MESH_FRAGMENT = `
uniform vec3 uColor;
uniform float uActivity;
uniform float uOpacity;
uniform vec3 uClipNormal;
uniform float uClipConstant;

varying vec3 vWorldPos;
varying vec3 vNormalW;

void main() {
  if (dot(uClipNormal, vWorldPos) + uClipConstant > 0.0) discard;
  vec3 viewDir = normalize(cameraPosition - vWorldPos);
  float rim = pow(1.0 - abs(dot(normalize(vNormalW), viewDir)), 2.2);
  float alpha = uOpacity * (0.22 + 0.78 * rim) * (0.6 + 0.5 * uActivity);
  vec3 color = uColor * (0.45 + 0.9 * uActivity) + vec3(0.16, 0.42, 0.52) * rim * 0.5;
  gl_FragColor = vec4(color, alpha);
}
`;

const WIRE_FRAGMENT = `
uniform vec3 uColor;
uniform float uOpacity;
uniform vec3 uClipNormal;
uniform float uClipConstant;

varying vec3 vWorldPos;
varying vec3 vNormalW;

void main() {
  if (dot(uClipNormal, vWorldPos) + uClipConstant > 0.0) discard;
  gl_FragColor = vec4(uColor, uOpacity);
}
`;

function makeTexture(array, type, width = array.length) {
  const texture = new THREE.DataTexture(array, width, 1, THREE.RedFormat, type);
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

function buildPointsGeometry(topology) {
  const { positions, regions } = topology;
  const count = regions.length;
  const colors = new Float32Array(count * 3);
  const indices = new Float32Array(count);
  const attack = new Float32Array(count);

  for (let i = 0; i < count; i += 1) {
    const color = REGION_COLORS[regions[i]] ?? [0.6, 0.6, 0.6];
    colors[i * 3] = color[0];
    colors[i * 3 + 1] = color[1];
    colors[i * 3 + 2] = color[2];
    indices[i] = i;
    attack[i] = regions[i] === 11 ? 1 : 0;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute("aIndex", new THREE.BufferAttribute(indices, 1));
  geometry.setAttribute("aAttack", new THREE.BufferAttribute(attack, 1));
  return geometry;
}

function buildGhostGeometry(topology) {
  const positions = topology.ghostPositions;
  const regions = topology.ghostRegions;
  const count = regions.length;
  if (!count) return null;

  const colors = new Float32Array(count * 3);
  const regionValues = new Float32Array(count);
  const indices = new Float32Array(count);

  for (let i = 0; i < count; i += 1) {
    const color = REGION_COLORS[regions[i]] ?? [0.5, 0.5, 0.5];
    colors[i * 3] = color[0];
    colors[i * 3 + 1] = color[1];
    colors[i * 3 + 2] = color[2];
    regionValues[i] = regions[i];
    indices[i] = i;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute("aRegion", new THREE.BufferAttribute(regionValues, 1));
  geometry.setAttribute("aIndex", new THREE.BufferAttribute(indices, 1));
  return geometry;
}

function buildEdgeGeometry(topology) {
  const { positions, edges, edgeSign, edgeWeight, regions } = topology;
  const edgeCount = edges.length / 2;
  const linePositions = new Float32Array(edgeCount * 6);
  const preIndices = new Float32Array(edgeCount * 2);
  const tValues = new Float32Array(edgeCount * 2);
  const colors = new Float32Array(edgeCount * 6);
  const weights = new Float32Array(edgeCount * 2);
  const kinds = new Float32Array(edgeCount * 2);

  for (let e = 0; e < edgeCount; e += 1) {
    const pre = edges[e * 2];
    const post = edges[e * 2 + 1];
    const base = e * 6;

    linePositions[base] = positions[pre * 3];
    linePositions[base + 1] = positions[pre * 3 + 1];
    linePositions[base + 2] = positions[pre * 3 + 2];
    linePositions[base + 3] = positions[post * 3];
    linePositions[base + 4] = positions[post * 3 + 1];
    linePositions[base + 5] = positions[post * 3 + 2];

    preIndices[e * 2] = pre;
    preIndices[e * 2 + 1] = pre;
    tValues[e * 2] = 0;
    tValues[e * 2 + 1] = 1;

    const isDan = regions[pre] === 7;
    const kind = isDan ? 2 : edgeSign[e] > 0 ? 0 : 1;
    const color =
      kind === 2
        ? SYNAPSE_COLORS.dopamine
        : kind === 1
          ? SYNAPSE_COLORS.inhibitory
          : SYNAPSE_COLORS.excitatory;
    colors[base] = color[0];
    colors[base + 1] = color[1];
    colors[base + 2] = color[2];
    colors[base + 3] = color[0];
    colors[base + 4] = color[1];
    colors[base + 5] = color[2];

    const weight = Math.min(1, Math.abs(edgeWeight[e]) / 1.6);
    weights[e * 2] = weight;
    weights[e * 2 + 1] = weight;
    kinds[e * 2] = kind;
    kinds[e * 2 + 1] = kind;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
  geometry.setAttribute("aPre", new THREE.BufferAttribute(preIndices, 1));
  geometry.setAttribute("aT", new THREE.BufferAttribute(tValues, 1));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute("aWeight", new THREE.BufferAttribute(weights, 1));
  geometry.setAttribute("aKind", new THREE.BufferAttribute(kinds, 1));
  return geometry;
}

function buildBounds(topology) {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (const array of [topology.positions, topology.ghostPositions]) {
    if (!array || !array.length) continue;
    for (let i = 0; i < array.length; i += 3) {
      for (let axis = 0; axis < 3; axis += 1) {
        const value = array[i + axis];
        if (value < min[axis]) min[axis] = value;
        if (value > max[axis]) max[axis] = value;
      }
    }
  }
  if (!Number.isFinite(min[0])) return { min: [-2, -2, -2], max: [2, 2, 3] };
  return { min, max };
}

function SceneContent({
  topology,
  connectome,
  attackPower,
  compact,
  view,
  filters,
  clip,
  timeScale,
  paused,
  explodeAmount,
  selectedIndex,
  onHover,
  onSelect,
  showBloom,
}) {
  const count = topology.regions.length;
  const { camera, raycaster } = useThree();
  const controlsRef = useRef(null);
  const simTimeRef = useRef(0);
  const lastSeq = useRef(-1);
  const lastTelemetryApplyAt = useRef(0);
  const explodeRef = useRef(0);
  const explodeTarget = useRef(0);
  const lastHoverAt = useRef(0);
  const regionActivityRef = useRef(new Array(12).fill(0));

  const pointsGeometry = useMemo(() => buildPointsGeometry(topology), [topology]);
  const ghostGeometry = useMemo(() => buildGhostGeometry(topology), [topology]);
  const edgeGeometry = useMemo(() => buildEdgeGeometry(topology), [topology]);
  const bounds = useMemo(() => buildBounds(topology), [topology]);

  const spikeArray = useMemo(() => {
    const array = new Float32Array(count);
    array.fill(-1000);
    return array;
  }, [count]);
  const voltageArray = useMemo(() => new Uint8Array(count), [count]);
  const spikeTexture = useMemo(() => makeTexture(spikeArray, THREE.FloatType), [spikeArray]);
  const voltageTexture = useMemo(
    () => makeTexture(voltageArray, THREE.UnsignedByteType),
    [voltageArray],
  );
  const regionTexture = useMemo(() => {
    const data = new Uint8Array(12);
    const texture = new THREE.DataTexture(data, 12, 1, THREE.RedFormat, THREE.UnsignedByteType);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = false;
    texture.needsUpdate = true;
    return texture;
  }, []);

  const clipState = useMemo(() => {
    if (!clip?.enabled) {
      return {
        enabled: false,
        normal: new THREE.Vector3(0, 0, 0),
        constant: CLIP_DISABLED,
        axis: 2,
        threshold: 0,
      };
    }
    const axis = clip.axis === "x" ? 0 : clip.axis === "y" ? 1 : 2;
    const value = Math.max(0, Math.min(1, clip.value ?? 0.5));
    const threshold = bounds.min[axis] + (bounds.max[axis] - bounds.min[axis]) * value;
    const normal = new THREE.Vector3(0, 0, 0);
    normal.setComponent(axis, 1);
    return { enabled: true, normal, constant: -threshold, axis, threshold };
  }, [clip, bounds]);

  const pointsMaterial = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          uSpikeTex: { value: spikeTexture },
          uVoltTex: { value: voltageTexture },
          uCount: { value: count },
          uTime: { value: 0 },
          uSize: { value: compact ? 0.18 : 0.13 },
          uAttack: { value: 0 },
          uExplode: { value: 0 },
          uCenter: { value: new THREE.Vector3(0, 0, 0.2) },
          uClipNormal: { value: new THREE.Vector3(0, 0, 0) },
          uClipConstant: { value: CLIP_DISABLED },
        },
        vertexShader: POINT_VERTEX,
        fragmentShader: POINT_FRAGMENT,
        transparent: true,
        depthWrite: false,
        blending: THREE.NormalBlending,
      }),
    [spikeTexture, voltageTexture, count, compact],
  );

  const ghostMaterial = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          uRegionTex: { value: regionTexture },
          uTime: { value: 0 },
          uSize: { value: compact ? 0.12 : 0.085 },
          uExplode: { value: 0 },
          uCenter: { value: new THREE.Vector3(0, 0, 0.2) },
          uClipNormal: { value: new THREE.Vector3(0, 0, 0) },
          uClipConstant: { value: CLIP_DISABLED },
        },
        vertexShader: GHOST_VERTEX,
        fragmentShader: GHOST_FRAGMENT,
        transparent: true,
        depthWrite: false,
        blending: THREE.NormalBlending,
      }),
    [regionTexture, compact],
  );

  const edgeMaterial = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          uSpikeTex: { value: spikeTexture },
          uCount: { value: count },
          uTime: { value: 0 },
          uSpeed: { value: 2.4 },
          uExplode: { value: 0 },
          uCenter: { value: new THREE.Vector3(0, 0, 0.2) },
          uFilter: { value: 0 },
          uMinWeight: { value: 0 },
          uClipNormal: { value: new THREE.Vector3(0, 0, 0) },
          uClipConstant: { value: CLIP_DISABLED },
        },
        vertexShader: EDGE_VERTEX,
        fragmentShader: EDGE_FRAGMENT,
        transparent: true,
        depthWrite: false,
        blending: THREE.NormalBlending,
      }),
    [spikeTexture, count],
  );

  const meshMaterials = useMemo(
    () =>
      topology.meshes.map((mesh) => {
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(mesh.vertices, 3));
        geometry.setIndex(new THREE.BufferAttribute(mesh.faces, 1));
        geometry.computeVertexNormals();
        const color = new THREE.Color(
          REGION_COLORS[mesh.group]?.[0] ?? 0.4,
          REGION_COLORS[mesh.group]?.[1] ?? 0.4,
          REGION_COLORS[mesh.group]?.[2] ?? 0.4,
        );
        const baseUniforms = {
          uColor: { value: color },
          uActivity: { value: 0 },
          uOpacity: { value: compact ? 0.14 : 0.1 },
          uExplode: { value: 0 },
          uCenter: { value: new THREE.Vector3(0, 0, 0.2) },
          uClipNormal: { value: new THREE.Vector3(0, 0, 0) },
          uClipConstant: { value: CLIP_DISABLED },
        };
        const filled = new THREE.ShaderMaterial({
          uniforms: { ...baseUniforms, uOpacity: { value: compact ? 0.14 : 0.1 } },
          vertexShader: MESH_VERTEX,
          fragmentShader: MESH_FRAGMENT,
          transparent: true,
          depthWrite: false,
          side: THREE.DoubleSide,
          blending: THREE.NormalBlending,
        });
        const wire = new THREE.ShaderMaterial({
          uniforms: { ...baseUniforms, uOpacity: { value: compact ? 0.1 : 0.16 } },
          vertexShader: MESH_VERTEX,
          fragmentShader: WIRE_FRAGMENT,
          transparent: true,
          depthWrite: false,
          side: THREE.DoubleSide,
          wireframe: true,
          blending: THREE.NormalBlending,
        });
        return { group: mesh.group, geometry, filled, wire };
      }),
    [topology, compact],
  );

  useEffect(() => {
    raycaster.params.Points.threshold = 0.055;
  }, [raycaster]);

  useEffect(() => {
    if (paused) return;
    const activity = connectome?.region_activity ?? {};
    const values = topology.regionNames.map((name) =>
      Math.min(1, (activity[name] ?? 0) * 24),
    );
    regionActivityRef.current = values;
    const data = regionTexture.image.data;
    for (let i = 0; i < 12; i += 1) {
      data[i] = Math.round((values[i] ?? 0) * 255);
    }
    regionTexture.needsUpdate = true;
  }, [connectome, paused, topology.regionNames, regionTexture]);

  useEffect(() => {
    if (!connectome || connectome.seq === lastSeq.current || paused) return;
    const nowPerf = performance.now();
    const minIntervalMs = timeScale < 1 ? 28 / Math.max(0.05, timeScale) : 0;
    if (minIntervalMs > 0 && nowPerf - lastTelemetryApplyAt.current < minIntervalMs) {
      return;
    }
    lastTelemetryApplyAt.current = nowPerf;
    lastSeq.current = connectome.seq;

    const bits = decodeSpikeBits(connectome.spikes_b64, count);
    const now = simTimeRef.current;
    for (let i = 0; i < count; i += 1) {
      if (bits[i]) spikeArray[i] = now;
    }

    const voltages = base64ToBytes(connectome.v_b64);
    voltageArray.set(voltages.subarray(0, count));

    spikeTexture.needsUpdate = true;
    voltageTexture.needsUpdate = true;
  }, [
    connectome,
    paused,
    timeScale,
    count,
    spikeArray,
    voltageArray,
    spikeTexture,
    voltageTexture,
  ]);

  useEffect(() => {
    const preset = VIEW_PRESETS[view] ?? VIEW_PRESETS.mosca;
    camera.position.set(...preset.position);
    explodeTarget.current = explodeAmount != null ? explodeAmount : preset.explode;
    if (controlsRef.current) {
      controlsRef.current.target.set(...preset.target);
      controlsRef.current.update();
    }
  }, [view, camera]);

  useEffect(() => {
    if (explodeAmount != null) {
      explodeTarget.current = explodeAmount;
    } else {
      const preset = VIEW_PRESETS[view] ?? VIEW_PRESETS.mosca;
      explodeTarget.current = preset.explode;
    }
  }, [explodeAmount, view]);

  const buildInfo = (index) => {
    if (index == null || index < 0 || index >= count) return null;
    const region = topology.regions[index];
    const biophysics = topology.biophysics ?? {};
    const vRest = biophysics.v_rest ?? -52;
    const vThresh = biophysics.v_thresh ?? -45;
    const low = vRest - 12;
    const high = vThresh + 6;
    const voltage = low + (voltageArray[index] / 255) * (high - low);
    const spikeTime = spikeArray[index];
    return {
      index,
      globalIndex: topology.visibleIdx?.[index] ?? index,
      region,
      regionName: topology.regionNames[region] ?? "Desconocida",
      voltage: Number(voltage.toFixed(2)),
      age: spikeTime > -100 ? Number((simTimeRef.current - spikeTime).toFixed(2)) : null,
      x: Number(topology.positions[index * 3].toFixed(3)),
      y: Number(topology.positions[index * 3 + 1].toFixed(3)),
      z: Number(topology.positions[index * 3 + 2].toFixed(3)),
    };
  };

  const handlePointerMove = (event) => {
    if (!onHover) return;
    event.stopPropagation();
    const now = performance.now();
    if (now - lastHoverAt.current < 70) return;
    lastHoverAt.current = now;
    onHover(buildInfo(event.index));
  };

  const handlePointerOut = () => {
    if (onHover) onHover(null);
  };

  const handleClick = (event) => {
    if (!onSelect) return;
    event.stopPropagation();
    onSelect(buildInfo(event.index));
  };

  const selected = useMemo(() => {
    if (selectedIndex == null || selectedIndex < 0 || selectedIndex >= count) return null;
    return [
      topology.positions[selectedIndex * 3],
      topology.positions[selectedIndex * 3 + 1],
      topology.positions[selectedIndex * 3 + 2],
    ];
  }, [selectedIndex, topology.positions, count]);

  const clipPlane = useMemo(() => {
    if (!clip?.enabled) return null;
    const axis = clipState.axis;
    const size = bounds.max.map((value, index) => value - bounds.min[index]);
    const center = bounds.max.map((value, index) => (value + bounds.min[index]) / 2);
    center[axis] = clipState.threshold;
    if (axis === 2) {
      return { position: center, rotation: [0, 0, 0], width: size[0] * 1.15, height: size[1] * 1.15 };
    }
    if (axis === 0) {
      return {
        position: center,
        rotation: [0, Math.PI / 2, 0],
        width: size[2] * 1.15,
        height: size[1] * 1.15,
      };
    }
    return {
      position: center,
      rotation: [Math.PI / 2, 0, 0],
      width: size[0] * 1.15,
      height: size[2] * 1.15,
    };
  }, [clip?.enabled, clipState, bounds]);

  useFrame((state, delta) => {
    if (!paused) simTimeRef.current += delta * timeScale;
    const elapsed = simTimeRef.current;

    explodeRef.current += (explodeTarget.current - explodeRef.current) * Math.min(1, delta * 4);
    const explode = explodeRef.current;
    const clipNormal = clipState.normal;
    const clipConstant = clipState.constant;

    pointsMaterial.uniforms.uTime.value = elapsed;
    pointsMaterial.uniforms.uAttack.value = attackPower;
    pointsMaterial.uniforms.uExplode.value = explode;
    pointsMaterial.uniforms.uClipNormal.value.copy(clipNormal);
    pointsMaterial.uniforms.uClipConstant.value = clipConstant;

    ghostMaterial.uniforms.uTime.value = elapsed;
    ghostMaterial.uniforms.uExplode.value = explode;
    ghostMaterial.uniforms.uClipNormal.value.copy(clipNormal);
    ghostMaterial.uniforms.uClipConstant.value = clipConstant;

    edgeMaterial.uniforms.uTime.value = elapsed;
    edgeMaterial.uniforms.uExplode.value = explode;
    edgeMaterial.uniforms.uFilter.value = filters?.kind ?? 0;
    edgeMaterial.uniforms.uMinWeight.value = filters?.minWeight ?? 0;
    edgeMaterial.uniforms.uClipNormal.value.copy(clipNormal);
    edgeMaterial.uniforms.uClipConstant.value = clipConstant;

    for (const mesh of meshMaterials) {
      const activity = regionActivityRef.current[mesh.group] ?? 0;
      for (const material of [mesh.filled, mesh.wire]) {
        material.uniforms.uActivity.value = activity;
        material.uniforms.uExplode.value = explode;
        material.uniforms.uClipNormal.value.copy(clipNormal);
        material.uniforms.uClipConstant.value = clipConstant;
      }
    }
  });

  useEffect(
    () => () => {
      pointsGeometry.dispose();
      ghostGeometry?.dispose();
      edgeGeometry.dispose();
      pointsMaterial.dispose();
      ghostMaterial.dispose();
      edgeMaterial.dispose();
      spikeTexture.dispose();
      voltageTexture.dispose();
      regionTexture.dispose();
      meshMaterials.forEach((mesh) => {
        mesh.geometry.dispose();
        mesh.filled.dispose();
        mesh.wire.dispose();
      });
    },
    [
      pointsGeometry,
      ghostGeometry,
      edgeGeometry,
      pointsMaterial,
      ghostMaterial,
      edgeMaterial,
      spikeTexture,
      voltageTexture,
      regionTexture,
      meshMaterials,
    ],
  );

  return (
    <>
      <color attach="background" args={["#181818"]} />
      <OrbitControls
        ref={controlsRef}
        enablePan={!compact}
        enableDamping
        dampingFactor={0.08}
        autoRotate={!paused && (VIEW_PRESETS[view]?.rotate ?? true)}
        autoRotateSpeed={0.55 * timeScale}
        minDistance={compact ? 5 : 3.5}
        maxDistance={compact ? 10 : 14}
      />
      <group>
        {meshMaterials.map((mesh) => (
          <mesh key={`fill-${mesh.group}`} geometry={mesh.geometry} material={mesh.filled} renderOrder={0} />
        ))}
        {!compact &&
          meshMaterials.map((mesh) => (
            <mesh key={`wire-${mesh.group}`} geometry={mesh.geometry} material={mesh.wire} renderOrder={1} />
          ))}
        {ghostGeometry && (
          <points geometry={ghostGeometry} material={ghostMaterial} renderOrder={2} frustumCulled={false} />
        )}
        <lineSegments geometry={edgeGeometry} material={edgeMaterial} renderOrder={3} frustumCulled={false} />
        <points
          geometry={pointsGeometry}
          material={pointsMaterial}
          renderOrder={4}
          frustumCulled={false}
          onPointerMove={compact ? undefined : handlePointerMove}
          onPointerOut={compact ? undefined : handlePointerOut}
          onClick={compact ? undefined : handleClick}
        />
        {clipPlane && (
          <mesh
            position={clipPlane.position}
            rotation={clipPlane.rotation}
            renderOrder={5}
          >
            <planeGeometry args={[clipPlane.width, clipPlane.height]} />
            <meshBasicMaterial
              color="#4285f4"
              transparent
              opacity={0.05}
              side={THREE.DoubleSide}
              depthWrite={false}
            />
          </mesh>
        )}
        {selected && (
          <Billboard position={selected} renderOrder={6}>
            <mesh>
              <ringGeometry args={[0.055, 0.082, 32]} />
              <meshBasicMaterial
                color="#ffffff"
                transparent
                opacity={0.95}
                side={THREE.DoubleSide}
                depthTest={false}
              />
            </mesh>
            <mesh>
              <ringGeometry args={[0.11, 0.125, 32]} />
              <meshBasicMaterial
                color="#448cff"
                transparent
                opacity={0.65}
                side={THREE.DoubleSide}
                depthTest={false}
              />
            </mesh>
          </Billboard>
        )}
      </group>
      {showBloom && (
        <EffectComposer multisampling={0}>
          <Bloom
            intensity={0.5}
            luminanceThreshold={0.28}
            luminanceSmoothing={0.35}
            mipmapBlur
          />
          <Vignette eskil={false} offset={0.18} darkness={0.62} />
        </EffectComposer>
      )}
    </>
  );
}

export default function ConnectomeScene({
  topology,
  connectome,
  attackPower = 0,
  compact = false,
  view = "mosca",
  filters,
  clip,
  timeScale = 1,
  paused = false,
  explodeAmount = null,
  selectedIndex = null,
  onHover,
  onSelect,
  bloom,
}) {
  const showBloom = bloom ?? !compact;
  return (
    <Canvas
      camera={{ position: VIEW_PRESETS.mosca.position, fov: 45 }}
      dpr={[1, compact ? 1.5 : 1.75]}
      gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
    >
      <SceneContent
        topology={topology}
        connectome={connectome}
        attackPower={attackPower}
        compact={compact}
        view={view}
        filters={filters}
        clip={clip}
        timeScale={timeScale}
        paused={paused}
        explodeAmount={explodeAmount}
        selectedIndex={selectedIndex}
        onHover={onHover}
        onSelect={onSelect}
        showBloom={showBloom}
      />
    </Canvas>
  );
}
