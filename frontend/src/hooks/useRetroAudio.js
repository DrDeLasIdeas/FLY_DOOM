import { useCallback, useEffect, useRef, useState } from "react";
import { RetroDoomAudioEngine } from "../audio/retroDoomAudio.js";

export function useRetroAudio(telemetry) {
  const engineRef = useRef(null);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [musicEnabled, setMusicEnabled] = useState(true);
  const [sfxEnabled, setSfxEnabled] = useState(true);
  const [volume, setVolumeState] = useState(0.45);
  const prevRef = useRef(null);

  if (!engineRef.current) {
    engineRef.current = new RetroDoomAudioEngine();
  }

  useEffect(() => {
    const eng = engineRef.current;
    return () => {
      eng?.dispose();
    };
  }, []);

  // Automatically pause/resume sequencer when simulation pauses/resumes
  useEffect(() => {
    const eng = engineRef.current;
    if (!eng || !audioEnabled) return;
    const running = telemetry?.system_running ?? true;
    if (!running || !musicEnabled) {
      eng._stopSequencer();
    } else {
      eng._startSequencer();
    }
  }, [audioEnabled, musicEnabled, telemetry?.system_running]);

  // Trigger reactive retro SFX from live telemetry deltas
  useEffect(() => {
    if (!telemetry) return;
    const curr = {
      shots: telemetry.total_shots ?? 0,
      kills: telemetry.total_kills ?? 0,
      health: telemetry.health ?? 100,
      episode: telemetry.episode ?? 1,
      scenarioId: telemetry.scenario?.id ?? "defend_the_center",
    };

    const prev = prevRef.current;
    prevRef.current = curr;
    if (!prev || !audioEnabled || !sfxEnabled) return;

    const eng = engineRef.current;
    if (!eng) return;

    if (curr.scenarioId !== prev.scenarioId) {
      eng.playScenarioSwitch();
      return;
    }
    if (curr.kills > prev.kills) {
      eng.playKill();
    } else if (curr.shots > prev.shots) {
      eng.playShot();
    }

    if (curr.episode === prev.episode) {
      if (curr.health < prev.health - 0.5) {
        eng.playDamage();
      } else if (curr.health > prev.health + 1.0) {
        eng.playPickup();
      }
    }
  }, [
    audioEnabled,
    sfxEnabled,
    telemetry?.total_shots,
    telemetry?.total_kills,
    telemetry?.health,
    telemetry?.episode,
    telemetry?.scenario?.id,
  ]);

  const toggleAudio = useCallback(() => {
    const eng = engineRef.current;
    if (!eng) return;
    const next = !audioEnabled;
    if (next) {
      eng.setMusicEnabled(true);
      eng.setSfxEnabled(true);
      setMusicEnabled(true);
      setSfxEnabled(true);
    }
    const ok = eng.setEnabled(next);
    setAudioEnabled(ok);
  }, [audioEnabled]);

  const toggleMusic = useCallback(() => {
    const eng = engineRef.current;
    if (!eng) return;
    if (!audioEnabled) {
      eng.setMusicEnabled(true);
      eng.setSfxEnabled(false);
      setMusicEnabled(true);
      setSfxEnabled(false);
      const ok = eng.setEnabled(true);
      setAudioEnabled(ok);
      return;
    }
    const next = !musicEnabled;
    eng.setMusicEnabled(next);
    setMusicEnabled(next);
    if (!next && !sfxEnabled) {
      eng.setEnabled(false);
      setAudioEnabled(false);
    }
  }, [audioEnabled, musicEnabled, sfxEnabled]);

  const toggleSfx = useCallback(() => {
    const eng = engineRef.current;
    if (!eng) return;
    if (!audioEnabled) {
      eng.setMusicEnabled(false);
      eng.setSfxEnabled(true);
      setMusicEnabled(false);
      setSfxEnabled(true);
      const ok = eng.setEnabled(true);
      setAudioEnabled(ok);
      if (ok) eng.playShot();
      return;
    }
    const next = !sfxEnabled;
    eng.setSfxEnabled(next);
    setSfxEnabled(next);
    if (next) {
      eng.playShot();
    } else if (!musicEnabled) {
      eng.setEnabled(false);
      setAudioEnabled(false);
    }
  }, [audioEnabled, sfxEnabled, musicEnabled]);

  const setVolume = useCallback((val) => {
    const eng = engineRef.current;
    const clean = Math.max(0, Math.min(1, Number(val) || 0));
    setVolumeState(clean);
    eng?.setVolume(clean);
  }, []);

  const triggerDopamineSfx = useCallback((valence) => {
    engineRef.current?.playDopamine(valence);
  }, []);

  return {
    audioEnabled,
    musicEnabled,
    sfxEnabled,
    volume,
    toggleAudio,
    toggleMusic,
    toggleSfx,
    setVolume,
    triggerDopamineSfx,
  };
}
