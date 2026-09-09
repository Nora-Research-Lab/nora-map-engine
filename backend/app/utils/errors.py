"""
Human-readable error handling.

Every error a user can trigger (bad file, unsupported format, oversized
upload, unreadable CRS, etc.) is raised as one of these typed exceptions and
turned into a plain-language JSON error by the handlers registered in
main.py. Nothing here ever leaks a Python traceback, a file path, or a
library name to the client.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all errors that should be shown to the user."""

    status_code: int = 400

    def __init__(self, message: str, *, hint: str | None = None):
        self.message = message
        self.hint = hint
        super().__init__(message)

    def to_dict(self) -> dict:
        body = {"error": self.message}
        if self.hint:
            body["hint"] = self.hint
        return body


class UnsupportedFormatError(AppError):
    def __init__(self, fmt: str, supported: list[str]):
        super().__init__(
            f"We can't read '{fmt}' files yet.",
            hint=f"Supported formats right now: {', '.join(supported)}.",
        )


class InvalidDatasetError(AppError):
    def __init__(self, message: str = "We couldn't find any usable geographic data in that file."):
        super().__init__(
            message,
            hint="Check that the file actually contains coordinates, geometry, or a CRS, "
            "then try again.",
        )


class NoCoordinatesError(AppError):
    def __init__(self):
        super().__init__(
            "Your file does not contain recognizable coordinates.",
            hint="For CSV files, make sure you have columns named something like "
            "'latitude'/'longitude' or 'lat'/'lon'.",
        )


class CRSDetectionError(AppError):
    def __init__(self):
        super().__init__(
            "We could not determine the coordinate system for this dataset.",
            hint="We'll assume WGS84 (EPSG:4326) so it still shows up on the map, "
            "but positions may be slightly off if that assumption is wrong.",
        )


class EmptyRasterError(AppError):
    def __init__(self):
        super().__init__(
            "Your raster contains no valid values.",
            hint="Every pixel came back as 'no data'. Double-check the file exported correctly.",
        )


class DatasetTooLargeError(AppError):
    def __init__(self, limit_mb: int):
        super().__init__(
            f"This file is larger than the {limit_mb} MB limit for direct upload.",
            hint="We recommend converting large rasters to Cloud Optimized GeoTIFF, or "
            "hosting large vector data as GeoParquet and adding it by URL instead.",
        )


class DatasetNotFoundError(AppError):
    status_code = 404

    def __init__(self, dataset_id: str):
        super().__init__(f"We couldn't find a dataset with id '{dataset_id}'.")


class LayerNotFoundError(AppError):
    status_code = 404

    def __init__(self, layer_id: str):
        super().__init__(f"We couldn't find a layer with id '{layer_id}'.")


class MapNotFoundError(AppError):
    status_code = 404

    def __init__(self, map_id: str):
        super().__init__(f"We couldn't find a saved map with id '{map_id}'.")


class ProcessingError(AppError):
    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message, hint=hint)


class RemoteFetchError(AppError):
    def __init__(self, message: str = "We couldn't fetch that dataset from its source."):
        super().__init__(
            message,
            hint="If you supplied a URL, make sure it's public and reachable, then try again.",
        )
