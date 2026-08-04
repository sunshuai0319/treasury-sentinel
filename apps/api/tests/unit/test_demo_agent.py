from app.agent.demo import run_demo_scenario


def test_demo_scenarios_have_expected_final_actions():
    expected = {
        "normal": "APPROVE",
        "duplicate": "REJECT",
        "address_mismatch": "REJECT",
        "over_limit": "REVIEW",
        "pause": "PAUSE",
    }

    for scenario, action in expected.items():
        run = run_demo_scenario(scenario)
        assert run.final_action == action
        assert run.timeline[-1].actor == "final"

