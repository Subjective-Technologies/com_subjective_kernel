from __future__ import annotations

from typing import Optional

from .types import (
    Action,
    AndP,
    AppValue,
    BoolValue,
    Condition,
    Context,
    FalseP,
    Feature,
    FeatureEq,
    FeatureValue,
    HasText,
    Hook,
    InApp,
    NotP,
    NumericValue,
    Op,
    OrP,
    OutcomePlan,
    TextValue,
    TimeAfter,
    TimeBefore,
    TimeValue,
    TrueP,
)


def context_has_text(text: str, ctx: Context) -> bool:
    for value in ctx.features.values():
        if isinstance(value, TextValue) and text in value.value:
            return True
    return False


def context_in_app(app: str, ctx: Context) -> bool:
    return ctx.app == app


def context_feature(feature: Feature, ctx: Context) -> Optional[FeatureValue]:
    return ctx.features.get(feature)


def eval_condition(condition: Condition, ctx: Context) -> bool:
    if isinstance(condition, TrueP):
        return True
    if isinstance(condition, FalseP):
        return False
    if isinstance(condition, HasText):
        return context_has_text(condition.text, ctx)
    if isinstance(condition, InApp):
        return context_in_app(condition.app, ctx)
    if isinstance(condition, TimeAfter):
        return ctx.time > condition.time
    if isinstance(condition, TimeBefore):
        return ctx.time < condition.time
    if isinstance(condition, FeatureEq):
        return context_feature(condition.feature, ctx) == condition.value
    if isinstance(condition, AndP):
        return eval_condition(condition.left, ctx) and eval_condition(condition.right, ctx)
    if isinstance(condition, OrP):
        return eval_condition(condition.left, ctx) or eval_condition(condition.right, ctx)
    if isinstance(condition, NotP):
        return not eval_condition(condition.cond, ctx)
    raise TypeError(f"Unsupported condition: {condition!r}")


def eval_action(action: Action, _ctx: Context) -> OutcomePlan:
    return action.action_plan


def eval_hook(hook: Hook, ctx: Context) -> Optional[OutcomePlan]:
    if eval_condition(hook.hook_condition, ctx):
        return eval_action(hook.hook_action, ctx)
    return None


def eval_outcome_plan(plan: OutcomePlan, _ctx: Context) -> float:
    return plan.plan_cost


def andP(c1: Condition, c2: Condition) -> Condition:
    if isinstance(c1, TrueP):
        return c2
    if isinstance(c2, TrueP):
        return c1
    if isinstance(c1, FalseP) or isinstance(c2, FalseP):
        return FalseP()
    return AndP(c1, c2)


def orP(c1: Condition, c2: Condition) -> Condition:
    if isinstance(c1, TrueP) or isinstance(c2, TrueP):
        return TrueP()
    if isinstance(c1, FalseP):
        return c2
    if isinstance(c2, FalseP):
        return c1
    return OrP(c1, c2)


def notP(c: Condition) -> Condition:
    if isinstance(c, TrueP):
        return FalseP()
    if isinstance(c, FalseP):
        return TrueP()
    if isinstance(c, NotP):
        return c.cond
    return NotP(c)


def hasText(text: str) -> Condition:
    return HasText(text)


def inApp(app: str) -> Condition:
    return InApp(app)


def timeAfter(t) -> Condition:
    return TimeAfter(t)


def timeBefore(t) -> Condition:
    return TimeBefore(t)


def featureEq(feature: Feature, value: FeatureValue) -> Condition:
    return FeatureEq(feature, value)


def _push_negations(c: Condition) -> Condition:
    if isinstance(c, NotP) and isinstance(c.cond, NotP):
        return _push_negations(c.cond.cond)
    if isinstance(c, NotP) and isinstance(c.cond, AndP):
        return OrP(_push_negations(NotP(c.cond.left)), _push_negations(NotP(c.cond.right)))
    if isinstance(c, NotP) and isinstance(c.cond, OrP):
        return AndP(_push_negations(NotP(c.cond.left)), _push_negations(NotP(c.cond.right)))
    if isinstance(c, NotP) and isinstance(c.cond, TrueP):
        return FalseP()
    if isinstance(c, NotP) and isinstance(c.cond, FalseP):
        return TrueP()
    if isinstance(c, AndP):
        return AndP(_push_negations(c.left), _push_negations(c.right))
    if isinstance(c, OrP):
        return OrP(_push_negations(c.left), _push_negations(c.right))
    return c


def _eliminate_identities(c: Condition) -> Condition:
    if isinstance(c, AndP):
        left = _eliminate_identities(c.left)
        right = _eliminate_identities(c.right)
        if isinstance(left, TrueP):
            return right
        if isinstance(right, TrueP):
            return left
        if isinstance(left, FalseP) or isinstance(right, FalseP):
            return FalseP()
        return AndP(left, right)
    if isinstance(c, OrP):
        left = _eliminate_identities(c.left)
        right = _eliminate_identities(c.right)
        if isinstance(left, FalseP):
            return right
        if isinstance(right, FalseP):
            return left
        if isinstance(left, TrueP) or isinstance(right, TrueP):
            return TrueP()
        return OrP(left, right)
    return c


def _flatten_ands(c: Condition) -> list[Condition]:
    if isinstance(c, AndP):
        return _flatten_ands(c.left) + _flatten_ands(c.right)
    return [c]


def _flatten_ors(c: Condition) -> list[Condition]:
    if isinstance(c, OrP):
        return _flatten_ors(c.left) + _flatten_ors(c.right)
    return [c]


def _build_and(cs: list[Condition]) -> Condition:
    if not cs:
        return TrueP()
    out = cs[0]
    for c in cs[1:]:
        out = AndP(out, c)
    return out


def _build_or(cs: list[Condition]) -> Condition:
    if not cs:
        return FalseP()
    out = cs[0]
    for c in cs[1:]:
        out = OrP(out, c)
    return out


def _flatten_condition(c: Condition) -> Condition:
    if isinstance(c, AndP):
        flat = [_flatten_condition(x) for x in _flatten_ands(_flatten_condition(c.left)) + _flatten_ands(_flatten_condition(c.right))]
        return _build_and(flat)
    if isinstance(c, OrP):
        flat = [_flatten_condition(x) for x in _flatten_ors(_flatten_condition(c.left)) + _flatten_ors(_flatten_condition(c.right))]
        return _build_or(flat)
    if isinstance(c, NotP):
        return NotP(_flatten_condition(c.cond))
    return c


def _condition_priority(c: Condition) -> int:
    if isinstance(c, TrueP):
        return 0
    if isinstance(c, FalseP):
        return 1
    if isinstance(c, HasText):
        return 2
    if isinstance(c, InApp):
        return 3
    if isinstance(c, TimeAfter):
        return 4
    if isinstance(c, TimeBefore):
        return 5
    if isinstance(c, FeatureEq):
        return 6
    if isinstance(c, NotP):
        return 7
    if isinstance(c, AndP):
        return 8
    if isinstance(c, OrP):
        return 9
    return 99


def _condition_sort_key(c: Condition) -> tuple[int, str]:
    return (_condition_priority(c), repr(c))


def _sort_condition(c: Condition) -> Condition:
    if isinstance(c, AndP):
        terms = _flatten_ands(AndP(_sort_condition(c.left), _sort_condition(c.right)))
        terms = sorted(terms, key=_condition_sort_key)
        return _build_and(terms)
    if isinstance(c, OrP):
        terms = _flatten_ors(OrP(_sort_condition(c.left), _sort_condition(c.right)))
        terms = sorted(terms, key=_condition_sort_key)
        return _build_or(terms)
    if isinstance(c, NotP):
        return NotP(_sort_condition(c.cond))
    return c


def normalize_condition(condition: Condition) -> Condition:
    return _sort_condition(_flatten_condition(_eliminate_identities(_push_negations(condition))))
