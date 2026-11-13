// Sistema Semántico de 4 Colores:
// Azul (#4285f4 / #448cff): Vía Sensorial (Retina, Lóbulo Óptico) y Giro Izquierdo (DNp20_L)
// Amarillo (#fbbc05): Memoria Asociativa (KC, Complejo Central), Umbrales y Giro Derecho (DNp20_R)
// Verde (#34a853): Recompensa Dopaminérgica (DAN PAM, MBON) y Carrera Frontal (DN Movimiento)
// Rojo (#ea4335): Combate, Ataque (DNp09) y Castigo Aversivo (PPL1)

export const REGION_COLORS = [
  [0.259, 0.522, 0.957], // 0: Retina Izquierda (Azul)
  [0.267, 0.549, 1.000], // 1: Retina Derecha (Azul Claro)
  [0.259, 0.522, 0.957], // 2: Lóbulo Óptico Izquierdo (Azul)
  [0.267, 0.549, 1.000], // 3: Lóbulo Óptico Derecho (Azul Claro)
  [0.984, 0.737, 0.020], // 4: Cuerpo del Hongo KC (Amarillo)
  [0.984, 0.737, 0.020], // 5: Complejo Central (Amarillo)
  [0.204, 0.659, 0.325], // 6: MBON Salida del Hongo (Verde)
  [0.204, 0.659, 0.325], // 7: DAN Dopamina (Verde)
  [0.259, 0.522, 0.957], // 8: DNp20 Izquierda (Azul)
  [0.984, 0.737, 0.020], // 9: DNp20 Derecha (Amarillo)
  [0.204, 0.659, 0.325], // 10: DN Movimiento / DNpe017 (Verde)
  [0.918, 0.263, 0.208], // 11: DNp09 Ataque (Rojo)
];

export const REGION_HEX = [
  "#4285f4", // 0: Retina Izquierda
  "#448cff", // 1: Retina Derecha
  "#4285f4", // 2: Lóbulo Óptico Izquierdo
  "#448cff", // 3: Lóbulo Óptico Derecho
  "#fbbc05", // 4: Cuerpo del Hongo (KC)
  "#fbbc05", // 5: Complejo Central
  "#34a853", // 6: MBON (Salida del Hongo)
  "#34a853", // 7: DAN (Dopamina)
  "#4285f4", // 8: DNp20 Izquierda
  "#fbbc05", // 9: DNp20 Derecha
  "#34a853", // 10: DN Movimiento
  "#ea4335", // 11: DNp09 Ataque
];

export const SYNAPSE_COLORS = {
  excitatory: [0.259, 0.522, 0.957], // Azul (#4285f4)
  inhibitory: [0.918, 0.263, 0.208], // Rojo (#ea4335)
  dopamine: [0.204, 0.659, 0.325],   // Verde (#34a853)
};

export const SYNAPSE_HEX = {
  excitatory: "#4285f4",
  inhibitory: "#ea4335",
  dopamine: "#34a853",
};

export const VOLTAGE_STOPS = [
  { at: 0.0, color: [0.259, 0.522, 0.957] },  // Basal (#4285f4 Azul)
  { at: 0.45, color: [0.204, 0.659, 0.325] }, // Homeostasis (#34a853 Verde)
  { at: 0.78, color: [0.984, 0.737, 0.020] }, // Umbral V_th (#fbbc05 Amarillo)
  { at: 1.0, color: [0.918, 0.263, 0.208] },  // Espiga de voltaje (#ea4335 Rojo)
];

export function voltageColor(value) {
  const v = Math.max(0, Math.min(1, value));
  for (let i = 1; i < VOLTAGE_STOPS.length; i += 1) {
    const previous = VOLTAGE_STOPS[i - 1];
    const next = VOLTAGE_STOPS[i];
    if (v <= next.at) {
      const t = (v - previous.at) / Math.max(1e-6, next.at - previous.at);
      return previous.color.map((c, idx) => c + (next.color[idx] - c) * t);
    }
  }
  return VOLTAGE_STOPS[VOLTAGE_STOPS.length - 1].color;
}
