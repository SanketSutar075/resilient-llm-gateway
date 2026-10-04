import pytest
from gateway.error_classifier import Action, classify
from gateway.errors import ProviderError


@pytest.mark.parametrize("status,action", [
    (429, Action.RETRY_THEN_SWITCH), (None, Action.RETRY_THEN_SWITCH),
    (401, Action.SWITCH), (402, Action.SWITCH), (500, Action.SWITCH), (503, Action.SWITCH),
    (400, Action.FAIL),
])
def test_actions(status, action):
    assert classify(ProviderError("x", status, "m")).action == action


def test_quota_gets_long_cooldown():
    assert classify(ProviderError("x", 402, "m")).cooldown_s >= 3600
