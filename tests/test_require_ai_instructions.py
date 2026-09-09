from tools.require_ai_instructions import missing


def test_agent_entrypoints_require_ai_instructions():
    assert missing() == [], missing()
