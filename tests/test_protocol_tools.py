import pytest
from agent.protocol import parse_action
from mcp_servers.logic import DocIndex, safe_calc
from agent.local_tools import DEFAULT_DOCS


def test_parse_plain_tool():
    a = parse_action('{"tool": "calculate", "args": {"expression": "1+1"}}')
    assert a.kind == "tool" and a.name == "calculate" and a.args == {"expression": "1+1"}


def test_parse_final_inside_code_fence_with_chatter():
    a = parse_action('Sure!\n```json\n{"final": "done"}\n```')
    assert a.kind == "final" and a.text == "done"


@pytest.mark.parametrize("bad", ["no json here", '{"tool": ', '[1,2]', '{"foo": 1}',
                                 '{"tool": "x", "final": "y"}', '{"tool": "x", "args": [1]}'])
def test_parse_invalid(bad):
    assert parse_action(bad).kind == "invalid"


def test_calc_basic_and_float_formatting():
    assert safe_calc("2+3*4") == "14"
    assert safe_calc("14/200*100") == "7"
    assert safe_calc("1/3") == "0.3333333333"


@pytest.mark.parametrize("bad", ["__import__('os').system('ls')", "open('x')", "1/0", "9**9**9", "2**1000",
                                 "abs(-1)", "a+1", "1+", "x" * 300])
def test_calc_rejects_unsafe_or_invalid(bad):
    with pytest.raises(ValueError):
        safe_calc(bad)


def test_docs_search_finds_relevant_policy():
    idx = DocIndex(DEFAULT_DOCS)
    out = idx.search("pour temperature range")
    assert out.startswith("[pour_temperature_policy.md]") and "700" in out
    assert "No matching" in idx.search("zebra unicorn")
