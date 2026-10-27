"""Bounded processing of indexed session captures, never camera or motor control."""

from __future__ import annotations

import asyncio
import errno
import io
from pathlib import Path
import tempfile
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from apps.backend.app.core.errors import AppError
from libs.astronomy.contracts.common import QualityProfile
from libs.astronomy.processing.planetary.pipeline import PlanetaryPipeline
from libs.devices.imaging import preview_png
from libs.devices.models import CapturedFrame
from libs.diagnostics.logging import get_logger
from libs.sessions.service import SessionService
from libs.storage.service import StorageService

logger = get_logger(__name__)


class ProcessingService:
    MAX_INPUT_BYTES = 32 * 1024**2
    MAX_PIXELS = 16_000_000

    def __init__(self, sessions: SessionService, storage: StorageService) -> None:
        self.sessions = sessions
        self.storage = storage
        self._lock = asyncio.Lock()

    async def planetary(self, session_id: str, file_ids: list[str], profile: QualityProfile) -> dict:
        if self._lock.locked():
            raise AppError("processing_busy", "Another processing job is running. Wait before retrying.", status_code=409)
        async with self._lock:
            worker = asyncio.get_running_loop().run_in_executor(None, self._planetary, session_id, file_ids, profile)
            cancelled = False
            while True:
                try:
                    result = await asyncio.shield(worker)
                    break
                except asyncio.CancelledError:
                    cancelled = True
            if cancelled:
                raise asyncio.CancelledError
            return result

    def _planetary(self, session_id: str, file_ids: list[str], profile: QualityProfile) -> dict:
        session = self.sessions.get_session(session_id)
        if session is None or session.status != "active":
            raise AppError("session_not_active", "Processing requires an existing active session.", status_code=409)
        if not 2 <= len(file_ids) <= 20 or len(set(file_ids)) != len(file_ids):
            raise AppError("processing_input", "Select 2–20 distinct captures.", status_code=422)
        indexed = {entry.file_id: entry for entry in self.storage.list_files(session_id)}
        inputs: list[tuple[Path, dict]] = []
        decoded_bytes = 0
        shape = None
        sensor_identity = None
        for file_id in file_ids:
            entry = indexed.get(file_id)
            path = self.storage.indexed_file_path(file_id) if entry is not None else None
            if entry is None or entry.kind != "capture" or path is None:
                raise AppError("processing_source", "Every input must be an available original capture in this session.", status_code=422)
            if path.stat().st_size > 64 * 1024**2:
                raise AppError("processing_memory", "A source file exceeds the 64 MiB input limit.", status_code=422)
            try:
                with Image.open(path) as header:
                    if header.format not in ("PNG", "PPM"):
                        raise AppError("processing_format", "Only captured PNG/PGM originals are supported.", status_code=422)
                    dimensions = (header.height, header.width)
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                raise AppError("processing_decode", "A source image cannot be read safely.", status_code=422) from exc
            if not 0 < dimensions[0] * dimensions[1] <= self.MAX_PIXELS:
                raise AppError("processing_memory", "A source exceeds the 16 megapixel limit.", status_code=422)
            decoded_bytes += dimensions[0] * dimensions[1] * 4
            if decoded_bytes > self.MAX_INPUT_BYTES:
                raise AppError("processing_memory", "Processing exceeds the 32 MiB float-input budget. Select fewer or smaller frames.", status_code=422)
            identity = tuple(entry.metadata.get(key) for key in ("generated_by", "camera_model", "camera_serial", "bit_depth", "bayer_pattern", "exposure_ms", "gain", "binning"))
            if shape is not None and (shape != dimensions or sensor_identity != identity):
                raise AppError("processing_mismatch", "Inputs must have identical dimensions, camera, raw format, exposure, gain and binning.", status_code=422)
            shape, sensor_identity = dimensions, identity
            inputs.append((path, entry.metadata))
        frames = []
        input_dtype = None
        for path, metadata in inputs:
            image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if image is None or image.shape[:2] != shape or image.dtype not in (np.uint8, np.uint16):
                raise AppError("processing_decode", "An input could not be decoded with its declared dimensions/depth.", status_code=422)
            if input_dtype is not None and image.dtype != input_dtype:
                raise AppError("processing_mismatch", "Input pixel depths differ.", status_code=422)
            input_dtype = image.dtype
            pattern = metadata.get("bayer_pattern")
            if pattern is not None:
                conversions = {"RGGB": cv2.COLOR_BayerRGGB2GRAY, "BGGR": cv2.COLOR_BayerBGGR2GRAY,
                               "GRBG": cv2.COLOR_BayerGRBG2GRAY, "GBRG": cv2.COLOR_BayerGBRG2GRAY}
                if pattern not in conversions or image.ndim != 2:
                    raise AppError("processing_format", "Invalid Bayer source.", status_code=422)
                image = cv2.cvtColor(image, conversions[pattern])
            elif image.ndim == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if image.ndim != 2 or np.ptp(image) == 0:
                raise AppError("processing_signal", "Each input needs a non-constant monochrome/luminance signal.", status_code=422)
            frames.append(image)
        try:
            with tempfile.TemporaryDirectory(prefix="telesco-planetary-") as stage:
                result = PlanetaryPipeline(profile).process(frames, stage)
                if not np.all(np.isfinite(result.stacked)):
                    raise AppError("processing_nonfinite", "The processing engine produced non-finite pixels.", status_code=422)
                image = np.rint(np.clip(result.stacked, 0, 1) * 65535).astype(np.uint16)
                ok, encoded = cv2.imencode(".png", image)
                if not ok:
                    raise AppError("processing_encode", "The processed image could not be encoded.", status_code=500)
                payload = encoded.tobytes()
                buffer = io.BytesIO()
                np.save(buffer, result.stacked, allow_pickle=False)
                frame = CapturedFrame(format="png", bytes_payload=payload, width=image.shape[1], height=image.shape[0])
                preview = preview_png(frame)
                token = uuid4().hex
                metadata = {
                    "pipeline": "planetary", "profile": profile.value, "source_file_ids": file_ids,
                    "source_implementation": inputs[0][1].get("generated_by", "unknown"),
                    "total_frames": result.total_frames, "selected_frames": result.selected_frames,
                    "normalized": True, "bit_depth": 16, "color_mode": "luminance",
                    "notes": [*result.notes, "Output is contrast-enhanced luminance, not calibrated photometry. Originals are unchanged."],
                }
                layout = self.storage.ensure_session_layout(session_id)
                items = []
                for kind, suffix, content in (
                    ("processed", ".png", payload), ("processed_array", ".npy", buffer.getvalue()),
                    ("preview", "_preview.png", preview),
                ):
                    directory = layout.previews_dir if kind == "preview" else layout.captures_dir
                    relative = str((directory / f"planetary_{token}{suffix}").relative_to(self.storage.root_dir))
                    self.storage.write_bytes_atomic(relative, content)
                    items.append(self.storage.index_file(session_id=session_id, kind=kind, relative_path=relative, metadata=metadata))
                return {"status": "ok", "file": items[0], "array": items[1], "preview": items[2],
                        "total_frames": result.total_frames, "selected_frames": result.selected_frames, "notes": metadata["notes"]}
        except (ValueError, MemoryError, cv2.error) as exc:
            logger.error("Planetary processing failed: %s", exc)
            raise AppError("processing_failed", "Planetary processing failed; inspect the inputs and server log.", status_code=422) from exc
        except OSError as exc:
            logger.error("Planetary output storage failed: %s", exc)
            raise AppError("storage_full" if exc.errno == errno.ENOSPC else "storage_write_failed",
                           "Processed output could not be saved.", status_code=507 if exc.errno == errno.ENOSPC else 500) from exc
