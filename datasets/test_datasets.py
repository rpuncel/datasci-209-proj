"""Tests for the lazy, cached dataset loaders."""

import io
import zipfile

import pandas as pd
import pytest

import datasets
from datasets import _sources
from datasets._sources import ZipDataset


def test_data_centers_warm_cache_no_network(monkeypatch):
    """With files already on disk, no download should be attempted."""

    def boom(*args, **kwargs):
        raise AssertionError("requests.get should not be called for a warm cache")

    monkeypatch.setattr(_sources.requests, "get", boom)

    df = datasets.data_centers()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Current total capital cost (2025 USD billions)" in df.columns


def test_memoization_returns_same_object():
    assert datasets.data_centers() is datasets.data_centers()


def test_cold_cache_downloads_once(tmp_path, monkeypatch):
    """A missing sentinel triggers exactly one download; a warm one triggers none."""
    sentinel = "hello.csv"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(sentinel, "a,b\n1,2\n")
    zip_bytes = buf.getvalue()

    calls = {"n": 0}

    class FakeResponse:
        content = zip_bytes

        def raise_for_status(self):
            pass

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        return FakeResponse()

    monkeypatch.setattr(_sources.requests, "get", fake_get)

    ds = ZipDataset(url="http://example/x.zip", dest=tmp_path / "x", sentinel=sentinel)

    assert ds.ensure() == tmp_path / "x"
    assert (tmp_path / "x" / sentinel).exists()
    assert calls["n"] == 1

    # Second call sees the warm cache and does not download again.
    ds.ensure()
    assert calls["n"] == 1
