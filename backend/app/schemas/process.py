from __future__ import annotations

from pydantic import BaseModel, Field


class HillshadeRequest(BaseModel):
    dataset_id: str
    azimuth: float = Field(315, ge=0, le=360)
    altitude: float = Field(45, ge=0, le=90)
    z_factor: float = Field(1.0, gt=0)


class SlopeRequest(BaseModel):
    dataset_id: str
    units: str = Field("degrees", pattern="^(degrees|percent)$")


class AspectRequest(BaseModel):
    dataset_id: str


class BufferRequest(BaseModel):
    dataset_id: str
    distance_m: float = Field(..., gt=0)


class ClipRequest(BaseModel):
    dataset_id: str
    mask_dataset_id: str


class ReprojectRequest(BaseModel):
    dataset_id: str
    target_crs: str = Field(..., examples=["EPSG:3857", "EPSG:4326"])


class RasterStatsRequest(BaseModel):
    dataset_id: str


class RasterCalculatorRequest(BaseModel):
    dataset_a_id: str
    dataset_b_id: str | None = None
    expression: str = Field(..., examples=["A - B", "A * 2", "(A - B) / (A + B)"])


class ProcessResult(BaseModel):
    dataset_id: str
    layer_suggested: bool = True
    message: str
