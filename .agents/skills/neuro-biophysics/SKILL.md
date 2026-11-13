---
name: neuro-biophysics
description: Reglas biofísicas obligatorias para programar el conectoma de Drosophila (LIF, R-STDP y ViZDoom).
---
# Reglas de Dominio: Neurobiología Computacional (FlyWire SNN)

1. **Parámetros Biológicos de Drosophila**:
   - Potencial de reposo $V_{rest} = -52.0\text{ mV}$, potencial de reset $V_{reset} = -52.0\text{ mV}$, umbral basal $V_{th} = -45.0\text{ mV}$.
   - Constantes de tiempo: $\tau_m = 20.0\text{ ms}$, $\tau_{syn} = 5.0\text{ ms}$.
2. **Eficiencia de Memoria**:
   - La matriz sináptica `W` debe ser un `torch.sparse_coo_tensor` coalescido. Prohibido usar `.to_dense()`.
3. **Límites de Seguridad Homeostática (Gemma 3)**:
   - `v_thresh` debe estar acotado estrictamente en $[-49.0, -41.0]\text{ mV}$.
   - `dopamine_lr` debe estar acotado en $[0.001, 0.05]$.
   - `motor_plastic_gain` debe acotarse con `torch.clamp(..., 0.4, 2.5)` para evitar saturación motora.

## Checklist de verificación
- [ ] ¿Se usa `torch.sparse.mm` para la propagación sináptica?
- [ ] ¿Están acotados (`clip`/`clamp`) todos los hiperparámetros recibidos desde Ollama?
- [ ] ¿Existe fallback si `vizdoom` o `ollama` no están activos?
