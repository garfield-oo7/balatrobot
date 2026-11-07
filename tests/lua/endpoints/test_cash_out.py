"""Tests for src/lua/endpoints/cash_out.lua"""

from typing import Any

import httpx

from tests.lua.conftest import (
    api,
    assert_error_response,
    assert_gamestate_response,
    load_fixture,
)


class TestCashOutEndpoint:
    """Test basic cash_out endpoint functionality."""

    def test_cash_out_from_ROUND_EVAL(self, client: httpx.Client) -> None:
        """Test cashing out from ROUND_EVAL state."""
        gamestate = load_fixture(client, "cash_out", "state-ROUND_EVAL")
        assert gamestate["state"] == "ROUND_EVAL"
        response = api(client, "cash_out", {})
        assert_gamestate_response(response, state="SHOP")


BLIND_REWARD = {"SMALL": 3, "BIG": 4, "BOSS": 5}


def expected_cash_out(gamestate: dict[str, Any]) -> int:
    """Cash out total for a ROUND_EVAL gamestate with no jokers or tags.

    Blind reward + $1 per hand left + $1 interest per $5 held (cap $5).
    """
    defeated = [
        blind["type"]
        for blind in gamestate["blinds"].values()
        if blind["status"] == "DEFEATED"
    ]
    order = ["SMALL", "BIG", "BOSS"]
    last = max(defeated, key=order.index)
    money = gamestate["money"]
    interest = min(money // 5, 5) if money >= 5 else 0
    return BLIND_REWARD[last] + gamestate["round"]["hands_left"] + interest


class TestCashOutEndpointPayout:
    """Test that cash_out pays the current round's total."""

    def test_cash_out_pays_current_round_total(self, client: httpx.Client) -> None:
        """Test that each cash out pays its own round, not the previous one.

        The game sets the cash out total in a late round-eval event, and the
        previous round's Cash Out button is never removed. Two rounds in one
        session are needed.
        """
        # Build the run with direct calls: loading a save drops the blind
        # reward from the loaded round's eval, and it also clears the old
        # Cash Out button.
        assert_gamestate_response(api(client, "menu", {}), state="MENU")
        assert_gamestate_response(
            api(client, "start", {"deck": "RED", "stake": "WHITE", "seed": "TEST123"}),
            state="BLIND_SELECT",
        )
        assert_gamestate_response(api(client, "select", {}), state="SELECTING_HAND")
        assert_gamestate_response(api(client, "set", {"chips": 1000}))
        gamestate = assert_gamestate_response(
            api(client, "play", {"cards": [0]}), state="ROUND_EVAL"
        )
        first_expected = expected_cash_out(gamestate)
        money_before = gamestate["money"]
        gamestate = assert_gamestate_response(api(client, "cash_out", {}), state="SHOP")
        assert gamestate["money"] - money_before == first_expected

        # Second round in the same session
        assert_gamestate_response(api(client, "next_round", {}), state="BLIND_SELECT")
        assert_gamestate_response(api(client, "select", {}), state="SELECTING_HAND")
        assert_gamestate_response(api(client, "set", {"chips": 1000}))
        gamestate = assert_gamestate_response(
            api(client, "play", {"cards": [0]}), state="ROUND_EVAL"
        )
        second_expected = expected_cash_out(gamestate)
        # The amounts must differ, or a stale payout could not be detected
        assert second_expected != first_expected
        money_before = gamestate["money"]
        gamestate = assert_gamestate_response(api(client, "cash_out", {}), state="SHOP")
        assert gamestate["money"] - money_before == second_expected


class TestCashOutEndpointStateRequirements:
    """Test cash_out endpoint state requirements."""

    def test_cash_out_from_BLIND_SELECT(self, client: httpx.Client):
        """Test that cash_out fails when not in ROUND_EVAL state."""
        gamestate = load_fixture(client, "cash_out", "state-BLIND_SELECT")
        assert gamestate["state"] == "BLIND_SELECT"
        assert_error_response(
            api(client, "cash_out", {}),
            "INVALID_STATE",
            "Method 'cash_out' requires one of these states: ROUND_EVAL",
        )
