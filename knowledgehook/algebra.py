from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from .semantics import andP, eval_condition, normalize_condition, orP
from .types import (
    Action,
    Alpha,
    AndP,
    AppValue,
    BoolValue,
    ClickElement,
    Context,
    Correction,
    Cost,
    Equiv,
    Feature,
    FeatureEq,
    FeatureValue,
    FalseP,
    HasText,
    Hook,
    HookMatch,
    HookStore,
    InApp,
    Metadata,
    NotP,
    NumericValue,
    Op,
    OpenApp,
    OrP,
    Outcome,
    OutcomePlan,
    Policy,
    RollbackPlan,
    Score,
    SendKeys,
    Sequence,
    Snapshot,
    Specificity,
    Stats,
    TextValue,
    TimeAfter,
    TimeBefore,
    TimeValue,
    TrueP,
    TypeText,
    UserInput,
    Wait,
    empty_context,
)


def estimate_cost(action: Action, _ctx: Context) -> Cost:
    return action.action_plan.plan_cost


def activate(store: HookStore, ctx: Context) -> list[HookMatch]:
    matches: list[HookMatch] = []
    for hook in store.hooks.values():
        if eval_condition(hook.hook_condition, ctx):
            matches.append(HookMatch(match_hook=hook, match_context=ctx, match_cost=estimate_cost(hook.hook_action, ctx)))
    return matches


def prioritize(_policy: Policy, matches: list[HookMatch]) -> HookMatch | None:
    if not matches:
        return None
    return min(matches, key=lambda m: (m.match_cost, -m.match_hook.hook_stats.stats_success))


def apply_op(op: Op, ctx: Context) -> Context:
    if isinstance(op, TypeText):
        f = Feature("typed_text", "text")
        new_features = dict(ctx.features)
        new_features[f] = TextValue(op.text)
        return replace(ctx, features=new_features)
    if isinstance(op, ClickElement):
        f = Feature("clicked_element", "ui")
        new_features = dict(ctx.features)
        new_features[f] = TextValue(op.element)
        return replace(ctx, features=new_features)
    if isinstance(op, OpenApp):
        return replace(ctx, app=op.app)
    if isinstance(op, SendKeys):
        f = Feature("sent_keys", "input")
        new_features = dict(ctx.features)
        new_features[f] = TextValue(op.keys)
        return replace(ctx, features=new_features)
    if isinstance(op, Wait):
        return replace(ctx, time=ctx.time + timedelta(seconds=op.seconds))
    if isinstance(op, Sequence):
        out = ctx
        for inner in op.ops:
            out = apply_op(inner, out)
        return out
    raise TypeError(f"Unsupported op: {op!r}")


def apply_op_sequence(ops: tuple[Op, ...], ctx: Context) -> Context:
    out = ctx
    for op in ops:
        out = apply_op(op, out)
    return out


def interpret_outcome_plan(plan: OutcomePlan, ctx: Context) -> tuple[Context, RollbackPlan]:
    new_ctx = apply_op_sequence(plan.plan_ops, ctx)
    return new_ctx, replace(plan.plan_rollback, rollback_context=ctx)


def interpret_action(action: Action, ctx: Context) -> tuple[Context, RollbackPlan]:
    return interpret_outcome_plan(action.action_plan, ctx)


def interpret_rollback(rollback_plan: RollbackPlan, current_ctx: Context) -> Context:
    context_after_rollback = apply_op_sequence(rollback_plan.rollback_ops, current_ctx)
    # Same semantics as Haskell mergeContexts: target fields win, current time is kept.
    return replace(rollback_plan.rollback_context, time=context_after_rollback.time)


def execute(hook: Hook, ctx: Context) -> Outcome:
    new_ctx, _rb = interpret_action(hook.hook_action, ctx)
    return Outcome(outcome_post=new_ctx, outcome_correction=False, outcome_plan=hook.hook_action.action_plan)


def infer_condition(before: Context, after: Context):
    if before.app != after.app:
        if after.app is not None:
            return InApp(after.app)
        return TrueP()
    return TrueP()


def invert_op(op: Op) -> Op:
    if isinstance(op, TypeText):
        return SendKeys("\b" * len(op.text))
    if isinstance(op, ClickElement):
        return ClickElement(op.element)
    if isinstance(op, OpenApp):
        return Wait(0.0)
    if isinstance(op, SendKeys):
        return SendKeys("\b" * len(op.keys))
    if isinstance(op, Wait):
        return Wait(0.0)
    if isinstance(op, Sequence):
        return Sequence(tuple(invert_op(i) for i in reversed(op.ops)))
    raise TypeError(f"Unsupported op: {op!r}")


def create_rollback_plan(ops: tuple[Op, ...]) -> RollbackPlan:
    return RollbackPlan(rollback_ops=tuple(invert_op(op) for op in reversed(ops)), rollback_context=empty_context())


def infer_action(user_input: UserInput) -> Action:
    return Action(
        action_plan=OutcomePlan(
            plan_ops=user_input.input_actions,
            plan_rollback=create_rollback_plan(user_input.input_actions),
            plan_cost=float(len(user_input.input_actions)),
        ),
        action_description="Learned from user input",
    )


def calculate_specificity(condition) -> Specificity:
    if isinstance(condition, TrueP):
        return 0.0
    if isinstance(condition, FalseP):
        return 1.0
    if isinstance(condition, HasText):
        return 0.3
    if isinstance(condition, InApp):
        return 0.4
    if isinstance(condition, TimeAfter) or isinstance(condition, TimeBefore):
        return 0.2
    if isinstance(condition, FeatureEq):
        return 0.5
    if isinstance(condition, AndP):
        return calculate_specificity(condition.left) + calculate_specificity(condition.right)
    if isinstance(condition, OrP):
        return min(calculate_specificity(condition.left), calculate_specificity(condition.right))
    if isinstance(condition, NotP):
        return calculate_specificity(condition.cond)
    raise TypeError(f"Unsupported condition: {condition!r}")


def learn_delta(alpha: Alpha, before: Snapshot, after: Snapshot, user_input: UserInput, store: HookStore) -> HookStore:
    _ = alpha
    delta_condition = infer_condition(before.snapshot_context, after.snapshot_context)
    delta_action = infer_action(user_input)
    hook_id = f"learned_{after.snapshot_id}"
    new_hook = Hook(
        hook_id=hook_id,
        hook_condition=delta_condition,
        hook_action=delta_action,
        hook_stats=Stats(stats_success=0.5, stats_uses=0, stats_corrections=0),
        hook_meta=Metadata(
            meta_created=user_input.input_time,
            meta_modified=user_input.input_time,
            meta_source="learned",
            meta_tags=("delta",),
        ),
        hook_specificity=calculate_specificity(delta_condition),
    )
    new_hooks = dict(store.hooks)
    new_hooks[new_hook.hook_id] = new_hook
    key = repr(normalize_condition(new_hook.hook_condition))
    new_indices = {k: list(v) for k, v in store.indices.items()}
    new_indices.setdefault(key, []).append(new_hook.hook_id)
    return HookStore(hooks=new_hooks, indices=new_indices)


def compose_nested(h1: Hook, h2: Hook) -> Hook:
    return Hook(
        hook_id=f"{h1.hook_id}_then_{h2.hook_id}",
        hook_condition=andP(h1.hook_condition, h2.hook_condition),
        hook_action=Action(
            action_plan=h1.hook_action.action_plan + h2.hook_action.action_plan,
            action_description=f"{h1.hook_action.action_description} then {h2.hook_action.action_description}",
        ),
        hook_stats=combine_stats(h1.hook_stats, h2.hook_stats),
        hook_meta=combine_metadata(h1.hook_meta, h2.hook_meta),
        hook_specificity=h1.hook_specificity + h2.hook_specificity,
    )


def compose_flat(h1: Hook, h2: Hook) -> Hook:
    return Hook(
        hook_id=f"{h1.hook_id}_and_{h2.hook_id}",
        hook_condition=orP(h1.hook_condition, h2.hook_condition),
        hook_action=Action(
            action_plan=h1.hook_action.action_plan + h2.hook_action.action_plan,
            action_description=f"{h1.hook_action.action_description} and {h2.hook_action.action_description}",
        ),
        hook_stats=combine_stats(h1.hook_stats, h2.hook_stats),
        hook_meta=combine_metadata(h1.hook_meta, h2.hook_meta),
        hook_specificity=min(h1.hook_specificity, h2.hook_specificity),
    )


def cascade(policy: Policy, store: HookStore, outcome: Outcome) -> list[Hook]:
    matches = activate(store, outcome.outcome_post)
    if policy.policy_max_cascade_depth > 0:
        top = prioritize(policy, matches)
        return [top.match_hook] if top else []
    return []


def refine(general: Hook, specific: Hook) -> Hook:
    return replace(
        specific,
        hook_condition=andP(general.hook_condition, specific.hook_condition),
        hook_specificity=general.hook_specificity + specific.hook_specificity,
    )


def equivalent(h1: Hook, h2: Hook) -> Equiv:
    same_condition = normalize_condition(h1.hook_condition) == normalize_condition(h2.hook_condition)
    same_action = h1.hook_action.action_plan == h2.hook_action.action_plan
    return Equiv.EQUIVALENT if same_condition and same_action else Equiv.NOT_EQUIVALENT


def negative_rl_update(alpha: Alpha, old_score: Score, correction: Correction) -> Score:
    c = 1.0 if correction else 0.0
    return (1.0 - alpha) * old_score + alpha * (1.0 - c)


def update_stats(alpha: Alpha, hook: Hook, correction: Correction) -> Hook:
    old = hook.hook_stats
    return replace(
        hook,
        hook_stats=Stats(
            stats_success=negative_rl_update(alpha, old.stats_success, correction),
            stats_uses=old.stats_uses + 1,
            stats_corrections=old.stats_corrections + (1 if correction else 0),
        ),
    )


def rollback(outcome: Outcome, ctx: Context) -> Context:
    return interpret_rollback(outcome.outcome_plan.plan_rollback, ctx)


def normalize_weights(h1: Hook, h2: Hook) -> tuple[Hook, Hook]:
    total_uses = h1.hook_stats.stats_uses + h2.hook_stats.stats_uses
    weight1 = (h1.hook_stats.stats_uses / total_uses) if total_uses > 0 else 0.5
    weight2 = 1.0 - weight1
    n1 = replace(h1, hook_stats=replace(h1.hook_stats, stats_success=weight1 * h1.hook_stats.stats_success))
    n2 = replace(h2, hook_stats=replace(h2.hook_stats, stats_success=weight2 * h2.hook_stats.stats_success))
    return n1, n2


def combine_hooks(h1: Hook, h2: Hook) -> Hook:
    return compose_flat(h1, h2)


def combine_stats(s1: Stats, s2: Stats) -> Stats:
    return Stats(
        stats_success=(s1.stats_success + s2.stats_success) / 2.0,
        stats_uses=s1.stats_uses + s2.stats_uses,
        stats_corrections=s1.stats_corrections + s2.stats_corrections,
    )


def combine_metadata(m1: Metadata, m2: Metadata) -> Metadata:
    return Metadata(
        meta_created=min(m1.meta_created, m2.meta_created),
        meta_modified=max(m1.meta_modified, m2.meta_modified),
        meta_source="composed",
        meta_tags=m1.meta_tags + m2.meta_tags,
    )
