"""Browser-compatible previews, independent of the camera's capture format."""

import cv2
import numpy as np

from libs.devices.interfaces import DeviceOperationError
from libs.devices.models import CapturedFrame


def preview_png(frame: CapturedFrame) -> bytes:
    image = cv2.imdecode(np.frombuffer(frame.bytes_payload, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise DeviceOperationError("camera_preview_format", "Camera frame could not be decoded.")
    if image.dtype == np.uint16:
        image = (image >> 8).astype(np.uint8)
    pattern = frame.metadata.get("bayer_pattern")
    if pattern is not None:
        conversions = {
            "RGGB": cv2.COLOR_BayerRGGB2BGR, "BGGR": cv2.COLOR_BayerBGGR2BGR,
            "GRBG": cv2.COLOR_BayerGRBG2BGR, "GBRG": cv2.COLOR_BayerGBRG2BGR,
        }
        if pattern not in conversions or image.ndim != 2:
            raise DeviceOperationError("camera_bayer_format", "Unsupported Bayer mosaic in camera frame.")
        image = cv2.cvtColor(image, conversions[pattern])
    if image.shape[1] > 1280:
        image = cv2.resize(image, (1280, max(1, round(image.shape[0] * 1280 / image.shape[1]))))
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise DeviceOperationError("camera_preview_encode", "Camera preview could not be encoded.")
    return encoded.tobytes()
