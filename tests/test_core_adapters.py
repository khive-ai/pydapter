import csv
import io
import json

import pytest
import toml

from pydapter.adapters import CsvAdapter, JsonAdapter, TomlAdapter


@pytest.mark.parametrize("adapter_key", ["json", "toml", "csv"])
def test_text_roundtrip(sample, adapter_key):
    dumped = sample.adapt_to(obj_key=adapter_key)
    restored = sample.__class__.adapt_from(dumped, obj_key=adapter_key)
    assert restored == sample
