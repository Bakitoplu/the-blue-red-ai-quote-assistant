import json
from pathlib import Path

import pytest

from app.models import ToolCallLog
from app.orchestrator import plan_and_execute
from app.schemas import ChatStreamRequest
from app.tools import get_quote

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = json.loads((ROOT / "the_blue_red_candidate_case_dataset" / "golden_test_scenarios.json").read_text(encoding="utf-8"))


def drain(db, scenario):
    req = ChatStreamRequest(
        quote_id=scenario["quote_id"],
        customer_id=scenario["customer_id"],
        channel=scenario["channel"],
        session_id=f"SES-{scenario['scenario_id']}",
        message_id=scenario["scenario_id"],
        message=scenario["user_message"],
        require_confirmation=False,
        mode="contract",
    )
    first = "".join(plan_and_execute(db, req))
    second = ""
    if scenario.get("repeat_same_message_id"):
        second = "".join(plan_and_execute(db, req))
    return first + second


def logs(db, scenario_id):
    return db.query(ToolCallLog).filter(ToolCallLog.message_id == scenario_id).order_by(ToolCallLog.sequence_no).all()


def active_items(db, quote_id, product_id):
    quote = get_quote(db, quote_id).data
    return [item for item in quote["items"] if item["product_id"] == product_id and item["status"] == "active"]


def item(db, quote_id, product_id):
    quote = get_quote(db, quote_id).data
    return next((row for row in quote["items"] if row["product_id"] == product_id), None)


def assert_subsequence(actual, expected):
    pos = 0
    for name in expected:
        while pos < len(actual) and actual[pos] != name:
            pos += 1
        assert pos < len(actual), f"{name} not found in {actual}"
        pos += 1


def nested_input(log, key):
    if key in log.input_json:
        return log.input_json[key]
    return (log.input_json.get("filters") or {}).get(key)


def assert_must_match(logs_for_scenario, expected_calls, events):
    cursor = 0
    for expected in expected_calls:
        name = expected["name"]
        if expected.get("must_match", {}).get("replayed"):
            assert '"replayed": true' in events
            continue
        match = None
        while cursor < len(logs_for_scenario):
            candidate = logs_for_scenario[cursor]
            cursor += 1
            if candidate.tool_name == name and candidate.success:
                match = candidate
                break
        assert match is not None, f"missing tool call {name}"
        for key, value in expected.get("must_match", {}).items():
            if key == "query_contains":
                assert value.casefold() in match.input_json.get("query", "").casefold()
            elif key == "required_tags":
                assert nested_input(match, key) == value
            elif key == "same_idempotency_key":
                assert '"replayed": true' in events
            else:
                assert nested_input(match, key) == value


def collected_sources(logs_for_scenario, events):
    sources = []
    for log in logs_for_scenario:
        sources.extend(log.source_ids or [])
    for line in events.splitlines():
        if line.startswith("data: ") and "source_id" in line:
            payload = json.loads(line[6:])
            if "source_id" in payload:
                sources.append(payload["source_id"])
            if "source_ids" in payload:
                sources.extend(payload["source_ids"])
    return set(sources)


def assert_not_recommended(logs_for_scenario, product_ids):
    for log in logs_for_scenario:
        if log.tool_name != "search_products":
            continue
        items = log.output_json.get("items", [])
        seen = {item.get("product_id") for item in items}
        for product_id in product_ids:
            assert product_id not in seen


def assert_quote_state(db, scenario_id):
    if scenario_id == "SCN-001":
        assert active_items(db, "Q-1002", "PRD-BC-110")[0]["quantity"] == 1
    elif scenario_id == "SCN-002":
        assert active_items(db, "Q-1001", "PRD-BC-130") == []
    elif scenario_id == "SCN-003":
        rows = active_items(db, "Q-1001", "PRD-BC-110")
        assert len(rows) == 1 and rows[0]["quantity"] == 3
    elif scenario_id == "SCN-004":
        assert active_items(db, "Q-1003", "PRD-PRN-320")[0]["quantity"] == 4
    elif scenario_id == "SCN-005":
        assert item(db, "Q-1004", "PRD-BC-120")["status"] == "replaced"
        assert active_items(db, "Q-1004", "PRD-BC-110")[0]["quantity"] == 1
    elif scenario_id == "SCN-006":
        assert item(db, "Q-1005", "PRD-BC-130")["status"] == "replaced"
        assert active_items(db, "Q-1005", "PRD-BC-140")[0]["quantity"] == 2
    elif scenario_id == "SCN-008":
        assert active_items(db, "Q-1002", "PRD-POS-210")
        assert active_items(db, "Q-1002", "PRD-SW-520")
    elif scenario_id == "SCN-010":
        assert active_items(db, "Q-1001", "PRD-BC-110")[0]["quantity"] == 2
    elif scenario_id == "SCN-011":
        quote = get_quote(db, "Q-1002").data
        assert active_items(db, "Q-1002", "PRD-BC-110")[0]["quantity"] == 3
        assert "RUL-PARTNER-3" in quote["discounts"]
    elif scenario_id == "SCN-012":
        assert active_items(db, "Q-2003", "PRD-ACC-710")[0]["quantity"] == 1
        assert active_items(db, "Q-2003", "PRD-ACC-710-PLUS")[0]["quantity"] == 4
    elif scenario_id == "SCN-013":
        assert active_items(db, "Q-2001", "PRD-BC-110-PLUS")[0]["quantity"] == 2
    elif scenario_id == "SCN-014":
        assert item(db, "Q-2004", "PRD-PRN-330")["status"] == "replaced"
        assert active_items(db, "Q-2004", "PRD-PRN-320")[0]["quantity"] == 1
    elif scenario_id == "SCN-015":
        assert active_items(db, "Q-2005", "PRD-SVC-810")[0]["quantity"] == 2
    elif scenario_id == "SCN-017":
        quote = get_quote(db, "Q-2002").data
        assert active_items(db, "Q-2002", "PRD-SW-520")
        assert active_items(db, "Q-2002", "PRD-SW-530")
        assert "RUL-SW-BUNDLE" in quote["discounts"]
    elif scenario_id == "SCN-019":
        quote = get_quote(db, "Q-2001").data
        assert active_items(db, "Q-2001", "PRD-BC-110-PLUS")[0]["quantity"] == 4
        assert "RUL-PLUS-QTY" in quote["discounts"]
    elif scenario_id == "SCN-020":
        assert active_items(db, "Q-1002", "PRD-BC-110")
        assert active_items(db, "Q-1002", "PRD-BC-110-PLUS") == []
    elif scenario_id == "SCN-022":
        assert active_items(db, "Q-2002", "PRD-ACC-740")[0]["quantity"] == 1
        assert active_items(db, "Q-2002", "PRD-ACC-730") == []


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["scenario_id"] for s in SCENARIOS])
def test_all_golden_scenarios(db, scenario):
    before = get_quote(db, scenario["quote_id"]).data
    events = drain(db, scenario)
    scenario_logs = logs(db, scenario["scenario_id"])
    names = [log.tool_name for log in scenario_logs]

    expected_names = [call["name"] for call in scenario["expected_tool_calls"] if not call.get("must_match", {}).get("replayed")]
    assert_subsequence(names, expected_names)
    assert_must_match(scenario_logs, scenario["expected_tool_calls"], events)

    for forbidden in scenario.get("must_not_call", []):
        assert forbidden not in names
    assert_not_recommended(scenario_logs, scenario.get("must_not_recommend", []))

    sources = collected_sources(scenario_logs, events)
    for source_id in scenario["expected_sources"]:
        assert source_id in sources

    assert_quote_state(db, scenario["scenario_id"])
    if scenario["scenario_id"] in {"SCN-007", "SCN-009", "SCN-016", "SCN-018", "SCN-021"}:
        after = get_quote(db, scenario["quote_id"]).data
        assert after == before
    if scenario["scenario_id"] == "SCN-018":
        assert "kesin vaat" not in events.casefold()
