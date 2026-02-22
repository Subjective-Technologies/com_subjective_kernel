from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
st = hypothesis.strategies

from knowledgehook.algebra import (
    cascade,
    equivalent,
    negative_rl_update,
    prioritize,
)
from knowledgehook.semantics import andP, eval_condition, normalize_condition, notP, orP
from knowledgehook.store import default_policy, empty_store
from knowledgehook.types import (
    Action,
    ClickElement,
    Context,
    Equiv,
    Feature,
    FeatureEq,
    FalseP,
    HasText,
    Hook,
    HookMatch,
    InApp,
    Metadata,
    OpenApp,
    Outcome,
    OutcomePlan,
    RollbackPlan,
    SendKeys,
    Snapshot,
    Stats,
    TextValue,
    TrueP,
    TypeText,
    UserInput,
    Wait,
    empty_context,
)


def _dt_strategy():
    return st.integers(min_value=0, max_value=500000).map(lambda s: datetime(2025, 1, 1, tzinfo=UTC) + timedelta(seconds=s))


@st.composite
def context_strategy(draw):
    app = draw(st.one_of(st.none(), st.sampled_from(["email", "calendar", "logger"])))
    text = draw(st.text(min_size=1, max_size=20))
    typed = draw(st.text(min_size=1, max_size=20))
    now = draw(_dt_strategy())
    features = {
        Feature("current_text", "text"): TextValue(text),
        Feature("typed_text", "text"): TextValue(typed),
    }
    return Context(features=features, time=now, app=app)


@st.composite
def condition_strategy(draw):
    atom = st.one_of(
        st.just(TrueP()),
        st.just(FalseP()),
        st.text(min_size=1, max_size=10).map(HasText),
        st.sampled_from(["email", "calendar", "logger"]).map(InApp),
        st.text(min_size=1, max_size=10).map(lambda t: FeatureEq(Feature("current_text", "text"), TextValue(t))),
    )
    return draw(
        st.recursive(
            atom,
            lambda c: st.one_of(
                st.tuples(c, c).map(lambda p: andP(p[0], p[1])),
                st.tuples(c, c).map(lambda p: orP(p[0], p[1])),
                c.map(notP),
            ),
            max_leaves=8,
        )
    ) 


@st.composite
def op_strategy(draw):
    atomic = st.one_of(
        st.text(min_size=1, max_size=15).map(TypeText),
        st.text(min_size=1, max_size=15).map(ClickElement),
        st.sampled_from(["email", "calendar", "logger"]).map(OpenApp),
        st.text(min_size=1, max_size=15).map(SendKeys),
        st.floats(min_value=0.0, max_value=5.0, allow_infinity=False, allow_nan=False).map(Wait),
    )
    return draw(atomic)


@st.composite
def hook_strategy(draw):
    cond = draw(condition_strategy())
    ops = tuple(draw(st.lists(op_strategy(), min_size=1, max_size=4)))
    cost = draw(st.floats(min_value=0.0, max_value=10.0, allow_infinity=False, allow_nan=False))
    success = draw(st.floats(min_value=0.0, max_value=1.0, allow_infinity=False, allow_nan=False))
    now = draw(_dt_strategy())
    idx = draw(st.integers(min_value=0, max_value=100000))
    return Hook(
        hook_id=f"h_{idx}",
        hook_condition=cond,
        hook_action=Action(
            action_plan=OutcomePlan(plan_ops=ops, plan_rollback=RollbackPlan(rollback_ops=(), rollback_context=empty_context()), plan_cost=cost),
            action_description="generated",
        ),
        hook_stats=Stats(stats_success=success, stats_uses=0, stats_corrections=0),
        hook_meta=Metadata(meta_created=now, meta_modified=now, meta_source="test", meta_tags=("generated",)),
        hook_specificity=0.0,
    )


@st.composite
def hook_match_strategy(draw):
    hook = draw(hook_strategy())
    ctx = draw(context_strategy())
    cost = draw(st.floats(min_value=0.0, max_value=10.0, allow_infinity=False, allow_nan=False))
    return HookMatch(match_hook=hook, match_context=ctx, match_cost=cost)


@st.composite
def same_cost_matches_strategy(draw):
    cost = draw(st.floats(min_value=0.0, max_value=10.0, allow_infinity=False, allow_nan=False))
    ctx = draw(context_strategy())
    h1 = draw(hook_strategy())
    s1 = draw(st.floats(min_value=0.0, max_value=1.0, allow_infinity=False, allow_nan=False))
    s2 = draw(st.floats(min_value=0.0, max_value=1.0, allow_infinity=False, allow_nan=False))
    h1 = Hook(
        hook_id=f"{h1.hook_id}_a",
        hook_condition=h1.hook_condition,
        hook_action=h1.hook_action,
        hook_stats=Stats(stats_success=s1, stats_uses=0, stats_corrections=0),
        hook_meta=h1.hook_meta,
        hook_specificity=h1.hook_specificity,
    )
    h2 = Hook(
        hook_id=f"{h1.hook_id}_b",
        hook_condition=h1.hook_condition,
        hook_action=h1.hook_action,
        hook_stats=Stats(stats_success=s2, stats_uses=0, stats_corrections=0),
        hook_meta=h1.hook_meta,
        hook_specificity=h1.hook_specificity,
    )
    return HookMatch(h1, ctx, cost), HookMatch(h2, ctx, cost)


@st.composite
def equivalent_hooks_strategy(draw):
    base = draw(hook_strategy())
    c = base.hook_condition
    eq_condition = andP(c, TrueP())
    copy = Hook(
        hook_id=f"{base.hook_id}_equiv",
        hook_condition=eq_condition,
        hook_action=base.hook_action,
        hook_stats=base.hook_stats,
        hook_meta=base.hook_meta,
        hook_specificity=base.hook_specificity,
    )
    return base, copy


@given(st.lists(hook_match_strategy(), min_size=1, max_size=20))
def test_minimization_law(matches):
    chosen = prioritize(default_policy(), matches)
    assert chosen is not None
    assert chosen.match_cost <= min(m.match_cost for m in matches)


@given(same_cost_matches_strategy())
def test_tie_breaking_law(pair):
    m1, m2 = pair
    chosen = prioritize(default_policy(), [m1, m2])
    assert chosen is not None
    if m1.match_hook.hook_stats.stats_success > m2.match_hook.hook_stats.stats_success:
        assert chosen == m1
    elif m2.match_hook.hook_stats.stats_success > m1.match_hook.hook_stats.stats_success:
        assert chosen == m2


@given(equivalent_hooks_strategy())
def test_equivalence_law(pair):
    h1, h2 = pair
    assert equivalent(h1, h2) == Equiv.EQUIVALENT


@given(condition_strategy(), condition_strategy(), condition_strategy(), context_strategy())
def test_boolean_algebra_associativity(c1, c2, c3, ctx):
    left = eval_condition(andP(andP(c1, c2), c3), ctx)
    right = eval_condition(andP(c1, andP(c2, c3)), ctx)
    assert left == right
    left_or = eval_condition(orP(orP(c1, c2), c3), ctx)
    right_or = eval_condition(orP(c1, orP(c2, c3)), ctx)
    assert left_or == right_or


@given(condition_strategy(), condition_strategy(), context_strategy())
def test_de_morgan(c1, c2, ctx):
    assert eval_condition(notP(andP(c1, c2)), ctx) == eval_condition(orP(notP(c1), notP(c2)), ctx)
    assert eval_condition(notP(orP(c1, c2)), ctx) == eval_condition(andP(notP(c1), notP(c2)), ctx)


@given(condition_strategy())
def test_normalization_idempotence(c):
    assert normalize_condition(normalize_condition(c)) == normalize_condition(c)


@given(st.integers(min_value=0, max_value=5))
def test_cascading_depth_limit(depth):
    policy = default_policy()
    policy = policy.__class__(
        policy_minimize_input=policy.policy_minimize_input,
        policy_success_weight=policy.policy_success_weight,
        policy_max_cascade_depth=depth,
    )
    out = Outcome(outcome_post=empty_context(), outcome_correction=False, outcome_plan=OutcomePlan.empty())
    cascaded = cascade(policy, empty_store(), out)
    assert len(cascaded) <= depth


@given(
    st.floats(min_value=0.001, max_value=0.999, allow_infinity=False, allow_nan=False),
    st.floats(min_value=0.0, max_value=1.0, allow_infinity=False, allow_nan=False),
)
def test_negative_rl_bounds(alpha, score):
    corrected = negative_rl_update(alpha, score, True)
    uncorrected = negative_rl_update(alpha, score, False)
    assert 0.0 <= corrected <= 1.0
    assert 0.0 <= uncorrected <= 1.0
