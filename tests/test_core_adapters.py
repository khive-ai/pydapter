import pytest
import json
import toml
import csv
import io
from pydapter.adapters import JsonAdapter, CsvAdapter, TomlAdapter


@pytest.mark.parametrize("adapter_key", ["json", "toml", "csv"])
def test_text_roundtrip(sample, adapter_key):
    dumped = sample.adapt_to(obj_key=adapter_key)
    restored = sample.__class__.adapt_from(dumped, obj_key=adapter_key)
    assert restored == sample
