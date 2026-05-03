from transport_types import TransportObject


def test_transport_object_alias_accepts_object_shaped_payload() -> None:
    payload: TransportObject = {"ok": True, "data": {"count": 1}}

    assert payload["ok"] is True
    assert payload["data"] == {"count": 1}
