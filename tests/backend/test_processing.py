"""Unit tests for the pure geoprocessing functions (no API layer)."""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import numpy as np
import pytest

from app.processing import raster_calc


def test_raster_calculator_basic_arithmetic():
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([[4.0, 3.0], [2.0, 1.0]])
    result = raster_calc.evaluate("A - B", a, b)
    assert np.allclose(result, a - b)


def test_raster_calculator_rejects_unknown_names():
    a = np.array([[1.0]])
    with pytest.raises(Exception):
        raster_calc.evaluate("__import__('os')", a)


def test_raster_calculator_rejects_unknown_band():
    a = np.array([[1.0]])
    with pytest.raises(Exception):
        raster_calc.evaluate("C + 1", a)


def test_intent_router_compare_two_domains():
    from app.services.intent_router import parse_intent

    result = parse_intent("compare geology and magnetic data")
    assert "geology" in result.domains
    assert "magnetic" in result.domains
    assert "compare" in result.actions
