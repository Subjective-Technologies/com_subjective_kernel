from datetime import UTC, datetime

from knowledgehook.demo import main
from knowledgehook.examples import example_seed_hook
from knowledgehook.semantics import eval_hook


def test_seed_hook_activates_in_example_context():
    now = datetime.now(tz=UTC)
    hook = example_seed_hook(now)
    plan = eval_hook(hook, hook.hook_action.action_plan.plan_rollback.rollback_context)
    assert plan is not None


def test_demo_runs(capsys):
    main()
    out = capsys.readouterr().out
    assert "Knowledge Hook Kernel Demo" in out
