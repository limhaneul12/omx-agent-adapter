import math

from omx_remote.shared.json_transport import (
    has_non_finite_float,
    is_json_object,
    is_json_value,
)


def test_json_transport_rejects_non_finite_floats() -> None:
    assert is_json_value(1.5)
    assert not is_json_value(math.nan)
    assert not is_json_value(math.inf)
    assert not is_json_value(-math.inf)
    assert not is_json_object({"value": math.nan})
    assert has_non_finite_float({"nested": (1.0, math.nan)})
