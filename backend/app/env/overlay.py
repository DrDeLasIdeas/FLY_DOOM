"""Visual overlay & telemetry detector (decoupled from RL pixel observations)."""

from __future__ import annotations

import cv2
import numpy as np

MONSTER_LABELS = {
    "Demon",
    "DoomImp",
    "ZombieMan",
    "ShotgunGuy",
    "ChaingunGuy",
    "HellKnight",
    "BaronOfHell",
    "Cacodemon",
    "LostSoul",
    "PainElemental",
    "Arachnotron",
    "Mancubus",
    "Revenant",
    "Archvile",
    "SpiderMastermind",
    "Cyberdemon",
}


class EnemyOverlayDetector:
    """Detects targets for HUD overlays and reward shaping without leaking into CNN inputs."""

    @staticmethod
    def empty() -> dict:
        return {
            "present": 0.0,
            "offset": 0.0,
            "size": 0.0,
            "centered": 0.0,
            "x": 0.0,
            "y": 0.0,
            "source": "NONE",
        }

    def detect_from_labels(self, labels, width: float = 320.0, height: float = 240.0) -> dict | None:
        best = None
        for label in labels or []:
            if label.object_name in MONSTER_LABELS:
                area = float(label.width * label.height)
                if area > 20.0 and (best is None or area > best[0]):
                    best = (area, label)
        if best is None:
            return None
        area, label = best
        cx = label.x + label.width / 2.0
        cy = label.y + label.height / 2.0
        offset = (cx - width / 2.0) / (width / 2.0)
        return {
            "present": 1.0,
            "offset": round(offset, 4),
            "size": round(area / (width * height), 5),
            "centered": 1.0 if abs(offset) < 0.12 else 0.0,
            "x": round(cx / width, 4),
            "y": round(cy / height, 4),
            "source": "LABEL",
        }

    def detect_from_color(self, rgb_frame: np.ndarray, is_combat: bool = True) -> dict | None:
        h, w = rgb_frame.shape[:2]
        roi = rgb_frame[: int(h * 0.78), :, :]
        r = roi[:, :, 0].astype(np.int16)
        g = roi[:, :, 1].astype(np.int16)
        b = roi[:, :, 2].astype(np.int16)
        if is_combat:
            mask = ((r > 80) & (r > g + 25) & (r > b + 25)).astype(np.uint8) * 255
            source = "RED"
        else:
            # Medkits / bright healing pickups in navigation scenarios
            mask = ((b > 120) & (g > 120) & (r < 120)).astype(np.uint8) * 255
            source = "MEDKIT"
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        contour = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(contour))
        if area < 40.0:
            return None
        x, y, cw, ch = cv2.boundingRect(contour)
        cx = x + cw / 2.0
        cy = y + ch / 2.0
        offset = (cx - w / 2.0) / (w / 2.0)
        return {
            "present": 1.0,
            "offset": round(offset, 4),
            "size": round(area / (w * h), 5),
            "centered": 1.0 if abs(offset) < 0.15 else 0.0,
            "x": round(cx / w, 4),
            "y": round(cy / h, 4),
            "source": source,
        }

    def detect(self, rgb_frame: np.ndarray, labels=None, is_combat: bool = True) -> dict:
        h, w = rgb_frame.shape[:2]
        detected = self.detect_from_labels(labels, width=float(w), height=float(h))
        if detected is None:
            detected = self.detect_from_color(rgb_frame, is_combat=is_combat)
        return detected if detected is not None else self.empty()

    @staticmethod
    def draw_overlay(frame: np.ndarray, target: dict, is_combat: bool = True) -> np.ndarray:
        if target.get("present", 0.0) < 0.5:
            return frame
        h, w = frame.shape[:2]
        cx = int(target["x"] * w)
        cy = int(target["y"] * h)
        color = (0, 255, 120) if target.get("centered", 0.0) > 0.5 else (0, 180, 255)
        cv2.circle(frame, (cx, cy), 18, color, 2)
        cv2.line(frame, (w // 2, h // 2), (cx, cy), color, 1)
        label = (
            ("TARGET LOCK" if target.get("centered", 0.0) > 0.5 else "HOSTILE")
            if is_combat
            else "MEDKIT"
        )
        cv2.putText(
            frame,
            label,
            (max(4, cx - 42), max(14, cy - 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            color,
            1,
            cv2.LINE_AA,
        )
        return frame
