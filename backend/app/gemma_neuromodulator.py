import json
import httpx
import numpy as np
from .config import settings


async def query_local_gemma_neuromodulator(
    telemetry_summary: dict, current_params: dict
) -> dict:
    prompt = f"""Eres el Sistema 2 (Neuromodulador Cortical) acoplado al conectoma biológico de Drosophila melanogaster (FlyWire) jugando DOOM.
Analiza la telemetría neurofisiológica actual:
{json.dumps(telemetry_summary, indent=2)}

Parámetros biofísicos actuales:
{json.dumps(current_params, indent=2)}

Reglas neurobiológicas:
1. Si mushroom_body_kc < 0.012, disminuye ligeramente "v_thresh" (hacia -46.5) o sube "sensory_gain".
2. Si mushroom_body_kc > 0.14, eleva "v_thresh" (hacia -43.5) para prevenir hiperexcitabilidad sináptica.
3. Ajusta "dopamine_lr" entre 0.002 y 0.04 según la recompensa reciente.

Responde ESTRICTAMENTE en JSON válido con este esquema:
{{
  "v_thresh": float,
  "dopamine_lr": float,
  "sensory_gain": float,
  "noise_std": float,
  "neuro_hypothesis": "Explicación científica concisa en español (máximo 2 oraciones)."
}}"""

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
            )
            response.raise_for_status()
            raw_json = response.json().get("response", "{}")
            parsed = json.loads(raw_json)
            return {
                "status": "ONLINE (Gemma 3 Local)",
                "model": settings.ollama_model,
                "v_thresh": round(
                    float(np.clip(parsed.get("v_thresh", current_params["v_thresh"]), -49.0, -41.0)),
                    2,
                ),
                "dopamine_lr": round(
                    float(np.clip(parsed.get("dopamine_lr", current_params["dopamine_lr"]), 0.001, 0.05)),
                    4,
                ),
                "sensory_gain": round(
                    float(np.clip(parsed.get("sensory_gain", current_params["sensory_gain"]), 8.0, 30.0)),
                    1,
                ),
                "noise_std": round(
                    float(np.clip(parsed.get("noise_std", current_params["noise_std"]), 0.2, 2.5)),
                    2,
                ),
                "neuro_hypothesis": parsed.get(
                    "neuro_hypothesis",
                    "Modulación homeostática ejecutada por Gemma 3 sobre el umbral LIF.",
                ),
            }
    except Exception:
        kc_rate = telemetry_summary.get("mushroom_body_kc", 0.03)
        delta = -0.25 if kc_rate < 0.015 else (0.20 if kc_rate > 0.12 else 0.0)
        new_v_thresh = round(float(np.clip(current_params["v_thresh"] + delta, -48.5, -42.0)), 2)
        return {
            "status": "HOMEOSTATIC_FALLBACK",
            "model": f"{settings.ollama_model} (Auto-Homeostasis)",
            "v_thresh": new_v_thresh,
            "dopamine_lr": current_params["dopamine_lr"],
            "sensory_gain": current_params["sensory_gain"],
            "noise_std": current_params["noise_std"],
            "neuro_hypothesis": (
                f"Bucle homeostático intrínseco activo (tasa KC={kc_rate:.4f}). "
                f"Umbral ajustado a {new_v_thresh} mV."
            ),
        }
