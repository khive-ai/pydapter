import pytest


@pytest.mark.parametrize("adapter_key", ["json", "toml", "csv"])
def test_text_roundtrip(sample, adapter_key):
    dumped = sample.adapt_to(obj_key=adapter_key)
    # For CSV adapter, we need to specify many=False to get a single object
    if adapter_key == "csv":
        restored = sample.__class__.adapt_from(dumped, obj_key=adapter_key, many=False)
    else:
        restored = sample.__class__.adapt_from(dumped, obj_key=adapter_key)
    assert restored == sample
