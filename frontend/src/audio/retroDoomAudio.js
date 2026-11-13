/**
 * RetroDoomAudioEngine — 100% Original, Royalty-Free Procedural Web Audio Synthesizer.
 *
 * Emulates early-90s AdLib / Sound Blaster 16 FM + Chiptune synthesis using pure
 * Web Audio API oscillators, noise buffers, filters, and waveshaping.
 * Zero external MP3/WAV assets and zero copyrighted melodies.
 */

const MIDI_TO_HZ = (midi) => 440 * Math.pow(2, (midi - 69) / 12);

// Original 32-step industrial Phrygian cyber-riff (MIDI notes; 0 = palm-mute rest)
const RIFF_STEPS = [
  // Bar 1: E2 pedal chug with F2 / G2 / Bb2 Phrygian tension
  40, 40, 0, 40, 41, 40, 0, 43,
  40, 40, 46, 45, 43, 41, 40, 0,
  // Bar 2: Syncopated climb + double-kick turnaround
  40, 40, 0, 40, 48, 47, 0, 46,
  45, 43, 41, 40, 41, 43, 46, 47,
];

const LEAD_ACCENTS = {
  4: 53,
  7: 55,
  10: 58,
  11: 57,
  20: 60,
  21: 59,
  23: 58,
  30: 58,
  31: 59,
};

function makeDistortionCurve(amount = 24) {
  const nSamples = 512;
  const curve = new Float32Array(nSamples);
  const deg = Math.PI / 180;
  for (let i = 0; i < nSamples; i += 1) {
    const x = (i * 2) / nSamples - 1;
    curve[i] = ((3 + amount) * x * 20 * deg) / (Math.PI + amount * Math.abs(x));
  }
  return curve;
}

export class RetroDoomAudioEngine {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.musicGain = null;
    this.sfxGain = null;
    this.distortionCurve = makeDistortionCurve(28);
    this.noiseBuffer = null;

    this.enabled = false;
    this.musicEnabled = true;
    this.sfxEnabled = true;
    this.volume = 0.45;
    this.bpm = 142;

    this._stepIndex = 0;
    this._nextNoteTime = 0;
    this._schedulerTimer = null;
    this._lastSfxAt = { shot: 0, kill: 0, damage: 0, pickup: 0 };
  }

  _ensureContext() {
    if (typeof window === "undefined") return null;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return null;
      this.ctx = new AudioCtx();

      const compressor = this.ctx.createDynamicsCompressor();
      compressor.threshold.value = -16;
      compressor.knee.value = 18;
      compressor.ratio.value = 6;
      compressor.attack.value = 0.004;
      compressor.release.value = 0.14;

      this.masterGain = this.ctx.createGain();
      this.musicGain = this.ctx.createGain();
      this.sfxGain = this.ctx.createGain();

      this.masterGain.gain.value = this.volume;
      this.musicGain.gain.value = this.musicEnabled ? 0.42 : 0.0;
      this.sfxGain.gain.value = this.sfxEnabled ? 0.85 : 0.0;

      this.musicGain.connect(this.masterGain);
      this.sfxGain.connect(this.masterGain);
      this.masterGain.connect(compressor);
      compressor.connect(this.ctx.destination);

      // Pre-generate 1 second of retro white noise for percussion & shotgun SFX
      const sampleRate = this.ctx.sampleRate;
      this.noiseBuffer = this.ctx.createBuffer(1, sampleRate, sampleRate);
      const data = this.noiseBuffer.getChannelData(0);
      for (let i = 0; i < sampleRate; i += 1) {
        data[i] = Math.random() * 2 - 1;
      }
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  setEnabled(nextEnabled) {
    this.enabled = Boolean(nextEnabled);
    if (this.enabled) {
      const ctx = this._ensureContext();
      if (!ctx) {
        this.enabled = false;
        return false;
      }
      this.masterGain.gain.setTargetAtTime(this.volume, ctx.currentTime, 0.02);
      this._startSequencer();
    } else {
      this._stopSequencer();
      if (this.ctx && this.masterGain) {
        this.masterGain.gain.setTargetAtTime(0.0001, this.ctx.currentTime, 0.02);
      }
    }
    return this.enabled;
  }

  setMusicEnabled(musicOn) {
    this.musicEnabled = Boolean(musicOn);
    if (this.ctx && this.musicGain) {
      this.musicGain.gain.setTargetAtTime(
        this.musicEnabled ? 0.42 : 0.0,
        this.ctx.currentTime,
        0.02
      );
    }
  }

  setVolume(vol) {
    this.volume = Math.max(0.0, Math.min(1.0, Number(vol) || 0));
    if (this.ctx && this.masterGain && this.enabled) {
      this.masterGain.gain.setTargetAtTime(this.volume, this.ctx.currentTime, 0.02);
    }
  }

  _startSequencer() {
    if (this._schedulerTimer || !this.ctx) return;
    this._stepIndex = 0;
    this._nextNoteTime = this.ctx.currentTime + 0.05;
    this._schedulerTimer = window.setInterval(() => this._scheduleAhead(), 25);
  }

  _stopSequencer() {
    if (this._schedulerTimer) {
      window.clearInterval(this._schedulerTimer);
      this._schedulerTimer = null;
    }
  }

  _scheduleAhead() {
    if (!this.enabled || !this.ctx) return;
    const stepDuration = 60.0 / this.bpm / 4.0; // 16th-note grid
    while (this._nextNoteTime < this.ctx.currentTime + 0.12) {
      if (this.musicEnabled) {
        this._scheduleStep(this._stepIndex, this._nextNoteTime, stepDuration);
      }
      this._nextNoteTime += stepDuration;
      this._stepIndex = (this._stepIndex + 1) % RIFF_STEPS.length;
    }
  }

  _scheduleStep(step, time, dur) {
    const midi = RIFF_STEPS[step];
    if (midi > 0) {
      this._triggerChugGuitar(MIDI_TO_HZ(midi), time, dur * 0.88, step % 4 === 0);
    }
    if (LEAD_ACCENTS[step]) {
      this._triggerFmLead(MIDI_TO_HZ(LEAD_ACCENTS[step]), time, dur * 1.35);
    }

    const barStep = step % 16;
    const isTurnaround = step >= 28;
    if (barStep === 0 || barStep === 6 || barStep === 8 || barStep === 14 || isTurnaround) {
      this._triggerKick(time);
    }
    if (barStep === 4 || barStep === 12) {
      this._triggerSnare(time);
    }
    if (step % 2 === 0) {
      this._triggerHiHat(time, barStep % 4 === 2);
    }
  }

  _triggerChugGuitar(freq, time, dur, accented) {
    const ctx = this.ctx;
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const shaper = ctx.createWaveShaper();
    const filter = ctx.createBiquadFilter();
    const env = ctx.createGain();

    osc1.type = "sawtooth";
    osc2.type = "square";
    osc1.frequency.setValueAtTime(freq, time);
    osc2.frequency.setValueAtTime(freq * 0.5, time); // sub-octave weight
    osc1.detune.value = -9;
    osc2.detune.value = 9;

    shaper.curve = this.distortionCurve;
    filter.type = "lowpass";
    filter.Q.value = 4.2;
    filter.frequency.setValueAtTime(accented ? 1350 : 920, time);
    filter.frequency.exponentialRampToValueAtTime(260, time + dur);

    const peak = accented ? 0.24 : 0.17;
    env.gain.setValueAtTime(0.0001, time);
    env.gain.linearRampToValueAtTime(peak, time + 0.006);
    env.gain.exponentialRampToValueAtTime(0.001, time + dur);

    osc1.connect(shaper);
    osc2.connect(shaper);
    shaper.connect(filter);
    filter.connect(env);
    env.connect(this.musicGain);

    osc1.start(time);
    osc2.start(time);
    osc1.stop(time + dur + 0.01);
    osc2.stop(time + dur + 0.01);
  }

  _triggerFmLead(freq, time, dur) {
    const ctx = this.ctx;
    const osc = ctx.createOscillator();
    const filter = ctx.createBiquadFilter();
    const env = ctx.createGain();

    osc.type = "square";
    osc.frequency.setValueAtTime(freq, time);
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(freq * 2.2, time);
    filter.Q.value = 2.5;

    env.gain.setValueAtTime(0.0001, time);
    env.gain.linearRampToValueAtTime(0.11, time + 0.008);
    env.gain.exponentialRampToValueAtTime(0.001, time + dur);

    osc.connect(filter);
    filter.connect(env);
    env.connect(this.musicGain);

    osc.start(time);
    osc.stop(time + dur + 0.01);
  }

  _triggerKick(time) {
    const ctx = this.ctx;
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(148, time);
    osc.frequency.exponentialRampToValueAtTime(42, time + 0.085);

    env.gain.setValueAtTime(0.42, time);
    env.gain.exponentialRampToValueAtTime(0.001, time + 0.095);

    osc.connect(env);
    env.connect(this.musicGain);
    osc.start(time);
    osc.stop(time + 0.1);
  }

  _triggerSnare(time) {
    const ctx = this.ctx;
    if (this.noiseBuffer) {
      const noise = ctx.createBufferSource();
      noise.buffer = this.noiseBuffer;
      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(1550, time);
      filter.Q.value = 1.2;
      const nEnv = ctx.createGain();
      nEnv.gain.setValueAtTime(0.24, time);
      nEnv.gain.exponentialRampToValueAtTime(0.001, time + 0.11);
      noise.connect(filter);
      filter.connect(nEnv);
      nEnv.connect(this.musicGain);
      noise.start(time);
      noise.stop(time + 0.12);
    }

    const body = ctx.createOscillator();
    const bEnv = ctx.createGain();
    body.type = "triangle";
    body.frequency.setValueAtTime(210, time);
    body.frequency.exponentialRampToValueAtTime(95, time + 0.07);
    bEnv.gain.setValueAtTime(0.2, time);
    bEnv.gain.exponentialRampToValueAtTime(0.001, time + 0.08);
    body.connect(bEnv);
    bEnv.connect(this.musicGain);
    body.start(time);
    body.stop(time + 0.085);
  }

  _triggerHiHat(time, open = false) {
    const ctx = this.ctx;
    if (!this.noiseBuffer) return;
    const dur = open ? 0.075 : 0.032;
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuffer;
    const hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.setValueAtTime(6800, time);
    const env = ctx.createGain();
    env.gain.setValueAtTime(open ? 0.1 : 0.065, time);
    env.gain.exponentialRampToValueAtTime(0.001, time + dur);
    src.connect(hp);
    hp.connect(env);
    env.connect(this.musicGain);
    src.start(time);
    src.stop(time + dur + 0.01);
  }

  // --- Reactive Retro Game SFX ---

  playShot() {
    if (!this.enabled || !this.sfxEnabled) return;
    const ctx = this._ensureContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    if (now - this._lastSfxAt.shot < 0.09) return;
    this._lastSfxAt.shot = now;

    // 1. Sub-boom barrel punch
    const boom = ctx.createOscillator();
    const boomEnv = ctx.createGain();
    boom.type = "sawtooth";
    boom.frequency.setValueAtTime(125, now);
    boom.frequency.exponentialRampToValueAtTime(34, now + 0.16);
    boomEnv.gain.setValueAtTime(0.38, now);
    boomEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
    boom.connect(boomEnv);
    boomEnv.connect(this.sfxGain);
    boom.start(now);
    boom.stop(now + 0.19);

    // 2. Crunchy shotgun blast noise
    if (this.noiseBuffer) {
      const blast = ctx.createBufferSource();
      blast.buffer = this.noiseBuffer;
      const bp = ctx.createBiquadFilter();
      bp.type = "bandpass";
      bp.frequency.setValueAtTime(980, now);
      bp.Q.value = 0.85;
      const nEnv = ctx.createGain();
      nEnv.gain.setValueAtTime(0.42, now);
      nEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.17);
      blast.connect(bp);
      bp.connect(nEnv);
      nEnv.connect(this.sfxGain);
      blast.start(now);
      blast.stop(now + 0.18);
    }
  }

  playKill() {
    if (!this.enabled || !this.sfxEnabled) return;
    const ctx = this._ensureContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    if (now - this._lastSfxAt.kill < 0.14) return;
    this._lastSfxAt.kill = now;

    // Retro demon-down growl + power chord confirmation
    const growl = ctx.createOscillator();
    const gEnv = ctx.createGain();
    growl.type = "sawtooth";
    growl.frequency.setValueAtTime(240, now);
    growl.frequency.exponentialRampToValueAtTime(52, now + 0.28);
    gEnv.gain.setValueAtTime(0.32, now);
    gEnv.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    growl.connect(gEnv);
    gEnv.connect(this.sfxGain);
    growl.start(now);
    growl.stop(now + 0.31);

    [329.63, 493.88, 659.25].forEach((hz, idx) => {
      const stab = ctx.createOscillator();
      const sEnv = ctx.createGain();
      stab.type = "square";
      const t = now + idx * 0.025;
      stab.frequency.setValueAtTime(hz, t);
      sEnv.gain.setValueAtTime(0.14, t);
      sEnv.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
      stab.connect(sEnv);
      sEnv.connect(this.sfxGain);
      stab.start(t);
      stab.stop(t + 0.23);
    });
  }

  playDamage() {
    if (!this.enabled || !this.sfxEnabled) return;
    const ctx = this._ensureContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    if (now - this._lastSfxAt.damage < 0.2) return;
    this._lastSfxAt.damage = now;

    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = "square";
    osc.frequency.setValueAtTime(155, now);
    osc.frequency.linearRampToValueAtTime(68, now + 0.14);
    env.gain.setValueAtTime(0.28, now);
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    osc.connect(env);
    env.connect(this.sfxGain);
    osc.start(now);
    osc.stop(now + 0.16);
  }

  playPickup() {
    if (!this.enabled || !this.sfxEnabled) return;
    const ctx = this._ensureContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    if (now - this._lastSfxAt.pickup < 0.18) return;
    this._lastSfxAt.pickup = now;

    [493.88, 659.25, 880.0].forEach((hz, i) => {
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type = "square";
      const t = now + i * 0.045;
      osc.frequency.setValueAtTime(hz, t);
      env.gain.setValueAtTime(0.16, t);
      env.gain.exponentialRampToValueAtTime(0.001, t + 0.11);
      osc.connect(env);
      env.connect(this.sfxGain);
      osc.start(t);
      osc.stop(t + 0.12);
    });
  }

  playDopamine(valence = 1.0) {
    if (!this.enabled || !this.sfxEnabled) return;
    const ctx = this._ensureContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = "triangle";
    if (valence >= 0) {
      osc.frequency.setValueAtTime(340, now);
      osc.frequency.exponentialRampToValueAtTime(920, now + 0.18);
    } else {
      osc.frequency.setValueAtTime(520, now);
      osc.frequency.exponentialRampToValueAtTime(160, now + 0.2);
    }
    env.gain.setValueAtTime(0.24, now);
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.21);
    osc.connect(env);
    env.connect(this.sfxGain);
    osc.start(now);
    osc.stop(now + 0.22);
  }

  playScenarioSwitch() {
    if (!this.enabled || !this.sfxEnabled) return;
    const ctx = this._ensureContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(190, now);
    osc.frequency.exponentialRampToValueAtTime(760, now + 0.24);
    env.gain.setValueAtTime(0.2, now);
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.26);
    osc.connect(env);
    env.connect(this.sfxGain);
    osc.start(now);
    osc.stop(now + 0.27);
  }

  dispose() {
    this._stopSequencer();
    if (this.ctx) {
      this.ctx.close().catch(() => {});
      this.ctx = null;
    }
  }
}
