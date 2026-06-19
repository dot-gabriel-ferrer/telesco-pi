"""Plate-solving request/response contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import RequestEnvelope


class ImageMetadata(BaseModel):
    width: int
    height: int
    format: str
    exposure_ms: float | None = None
    gain: float | None = None
    pixel_scale_hint_arcsec_px: float | None = None


class SearchHint(BaseModel):
    ra_deg_guess: float | None = None
    dec_deg_guess: float | None = None
    fov_deg_guess: float | None = None
    pixel_scale_arcsec_px: float | None = None


class SolveRequest(RequestEnvelope):
    image_path: str
    metadata: ImageMetadata
    hint: SearchHint = Field(default_factory=SearchHint)


class SolveDiagnostics(BaseModel):
    stars_used: int = 0
    residual_arcsec: float | None = None
    runtime_ms: float = 0.0
    reason_if_failed: str | None = None
    index_files_used: list[str] = Field(default_factory=list)


class SolveResponse(BaseModel):
    status: str
    center_ra_deg: float | None = None
    center_dec_deg: float | None = None
    pixel_scale_arcsec_px: float | None = None
    orientation_deg: float | None = None
    field_size_deg: tuple[float, float] | None = None
    confidence_score: float = 0.0
    diagnostics: SolveDiagnostics = Field(default_factory=SolveDiagnostics)
