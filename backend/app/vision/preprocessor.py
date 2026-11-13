"""Visual Buffer Preprocessing Pipeline for VIZDOOM_NATIVE & Synthetic RGB frames.

Pipeline per frame:
    RGB (H, W, 3) uint8
      -> Grayscale conversion (+ optional subtle red-channel emphasis)
      -> Resize to (84, 84) via cv2.INTER_AREA
      -> Normalize to float32 in [0.0, 1.0]
      -> Temporal FrameStack deque(maxlen=k) -> Tensor (k, 84, 84) float32

Also produces:
    - 64x64 uint8 retinal matrix for the biological Drosophila SNN.
    - Base64-encoded 2x2 FrameStack mosaic so the live UI displays the exact
      processed visual buffer perceived by the PPO CNN.
"""

from __future__ import annotations

import base64
from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np

from ..core.interfaces import VisualPreprocessor


@dataclass(frozen=True)
class VisualBufferConfig:
    """Configuration parameters for the visual preprocessing pipeline."""

    width: int = 84
    height: int = 84
    stack_size: int = 4
    grayscale: bool = True
    normalize: bool = True
    red_boost: float = 0.15


class VisualBufferProcessor(VisualPreprocessor):
    """Stateless-per-frame + stateful-temporal stack visual buffer processor."""

    def __init__(self, config: VisualBufferConfig | None = None):
        self.config = config or VisualBufferConfig()
        self._stack: deque[np.ndarray] = deque(maxlen=self.config.stack_size)
        self._blank = np.zeros(
            (self.config.stack_size, self.config.height, self.config.width),
            dtype=np.float32,
        )

    @property
    def output_shape(self) -> tuple[int, ...]:
        return (self.config.stack_size, self.config.height, self.config.width)

    def reset(self) -> None:
        self._stack.clear()

    def _preprocess_single(self, frame: np.ndarray) -> np.ndarray:
        arr = np.asarray(frame)
        if arr.ndim == 2:
            gray = arr.astype(np.uint8)
        elif arr.ndim == 3 and arr.shape[2] >= 3:
            rgb = arr[:, :, :3].astype(np.uint8)
            if self.config.grayscale:
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
                if self.config.red_boost > 0.0:
                    red_signal = cv2.subtract(rgb[:, :, 0], gray // 2)
                    gray = cv2.addWeighted(
                        gray,
                        1.0 - self.config.red_boost,
                        red_signal,
                        self.config.red_boost,
                        0,
                    )
            else:
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr.squeeze().astype(np.uint8)

        resized = cv2.resize(
            gray,
            (self.config.width, self.config.height),
            interpolation=cv2.INTER_AREA,
        )
        if self.config.normalize:
            return (resized.astype(np.float32) / 255.0).clip(0.0, 1.0)
        return resized.astype(np.float32)

    def process(self, rgb_frame: np.ndarray) -> np.ndarray:
        processed = self._preprocess_single(rgb_frame)
        if len(self._stack) == 0:
            for _ in range(self.config.stack_size):
                self._stack.append(processed)
        else:
            self._stack.append(processed)
        return np.stack(self._stack, axis=0).astype(np.float32)

    def latest_frame(self) -> np.ndarray:
        if len(self._stack) == self.config.stack_size:
            return np.stack(self._stack, axis=0).astype(np.float32)
        return self._blank.copy()

    def compute_retina_64(self, rgb_frame: np.ndarray) -> np.ndarray:
        arr = np.asarray(rgb_frame)
        if arr.ndim == 2:
            composite = arr.astype(np.uint8)
        else:
            rgb = arr[:, :, :3].astype(np.uint8)
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            red_boost = cv2.subtract(rgb[:, :, 0], gray // 2)
            composite = cv2.addWeighted(gray, 0.7, red_boost, 0.3, 0)
        return cv2.resize(composite, (64, 64), interpolation=cv2.INTER_AREA)

    def encode_stack_mosaic_b64(self, quality: int = 80) -> str:
        """Encodes the 4-frame stack into a 2x2 grayscale JPEG for live inspection."""
        stack = self.latest_frame()
        frames_u8 = [
            np.clip(frame * 255.0 if self.config.normalize else frame, 0, 255).astype(np.uint8)
            for frame in stack
        ]
        while len(frames_u8) < 4:
            frames_u8.insert(0, np.zeros((self.config.height, self.config.width), dtype=np.uint8))

        h, w = self.config.height, self.config.width
        mosaic = np.zeros((h * 2, w * 2), dtype=np.uint8)
        mosaic[:h, :w] = frames_u8[0]
        mosaic[:h, w:] = frames_u8[1]
        mosaic[h:, :w] = frames_u8[2]
        mosaic[h:, w:] = frames_u8[3]

        bgr = cv2.cvtColor(mosaic, cv2.COLOR_GRAY2BGR)
        cv2.line(bgr, (w, 0), (w, h * 2), (66, 133, 244), 1)
        cv2.line(bgr, (0, h), (w * 2, h), (66, 133, 244), 1)
        labels = ["t-3", "t-2", "t-1", "t"]
        coords = [(4, 12), (w + 4, 12), (4, h + 12), (w + 4, h + 12)]
        for text, (x, y) in zip(labels, coords):
            cv2.putText(
                bgr,
                text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.34,
                (52, 168, 83) if text == "t" else (200, 200, 200),
                1,
                cv2.LINE_AA,
            )

        ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return ""
        return base64.b64encode(buf).decode("utf-8")
