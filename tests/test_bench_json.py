from pydapter.adapters import JsonAdapter


def test_json_perf(benchmark, sample):
    """Benchmark the performance of JsonAdapter.to_obj."""
    benchmark(JsonAdapter.to_obj, sample)
