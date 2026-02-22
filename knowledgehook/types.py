from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Optional, Union


HookId = str
Alpha = float
Score = float
Cost = float
Specificity = float
Correction = bool


@dataclass(frozen=True, order=True)
class Feature:
    feature_name: str
    feature_type: str


@dataclass(frozen=True)
class TextValue:
    value: str


@dataclass(frozen=True)
class AppValue:
    value: str


@dataclass(frozen=True)
class TimeValue:
    value: datetime


@dataclass(frozen=True)
class NumericValue:
    value: float


@dataclass(frozen=True)
class BoolValue:
    value: bool


FeatureValue = Union[TextValue, AppValue, TimeValue, NumericValue, BoolValue]


@dataclass(frozen=True)
class Context:
    features: dict[Feature, FeatureValue]
    time: datetime
    app: Optional[str]


def empty_context() -> Context:
    return Context(features={}, time=datetime(1970, 1, 1, tzinfo=UTC), app=None)


@dataclass(frozen=True)
class TrueP:
    pass


@dataclass(frozen=True)
class FalseP:
    pass


@dataclass(frozen=True)
class HasText:
    text: str


@dataclass(frozen=True)
class InApp:
    app: str


@dataclass(frozen=True)
class TimeAfter:
    time: datetime


@dataclass(frozen=True)
class TimeBefore:
    time: datetime


@dataclass(frozen=True)
class FeatureEq:
    feature: Feature
    value: FeatureValue


@dataclass(frozen=True)
class AndP:
    left: "Condition"
    right: "Condition"


@dataclass(frozen=True)
class OrP:
    left: "Condition"
    right: "Condition"


@dataclass(frozen=True)
class NotP:
    cond: "Condition"


Condition = Union[TrueP, FalseP, HasText, InApp, TimeAfter, TimeBefore, FeatureEq, AndP, OrP, NotP]


@dataclass(frozen=True)
class TypeText:
    text: str


@dataclass(frozen=True)
class ClickElement:
    element: str


@dataclass(frozen=True)
class OpenApp:
    app: str


@dataclass(frozen=True)
class SendKeys:
    keys: str


@dataclass(frozen=True)
class Wait:
    seconds: float


@dataclass(frozen=True)
class Sequence:
    ops: tuple["Op", ...]


Op = Union[TypeText, ClickElement, OpenApp, SendKeys, Wait, Sequence]


@dataclass(frozen=True)
class RollbackPlan:
    rollback_ops: tuple[Op, ...]
    rollback_context: Context

    def __add__(self, other: "RollbackPlan") -> "RollbackPlan":
        return RollbackPlan(rollback_ops=other.rollback_ops + self.rollback_ops, rollback_context=self.rollback_context)


@dataclass(frozen=True)
class OutcomePlan:
    plan_ops: tuple[Op, ...]
    plan_rollback: RollbackPlan
    plan_cost: Cost

    def __add__(self, other: "OutcomePlan") -> "OutcomePlan":
        return OutcomePlan(
            plan_ops=self.plan_ops + other.plan_ops,
            plan_rollback=other.plan_rollback + self.plan_rollback,
            plan_cost=self.plan_cost + other.plan_cost,
        )

    @staticmethod
    def empty() -> "OutcomePlan":
        return OutcomePlan(plan_ops=(), plan_rollback=RollbackPlan(rollback_ops=(), rollback_context=empty_context()), plan_cost=0.0)


@dataclass(frozen=True)
class Action:
    action_plan: OutcomePlan
    action_description: str


@dataclass(frozen=True)
class Outcome:
    outcome_post: Context
    outcome_correction: Correction
    outcome_plan: OutcomePlan


@dataclass(frozen=True)
class Stats:
    stats_success: Score
    stats_uses: int
    stats_corrections: int


@dataclass(frozen=True)
class Metadata:
    meta_created: datetime
    meta_modified: datetime
    meta_source: str
    meta_tags: tuple[str, ...]


@dataclass(frozen=True)
class Hook:
    hook_id: HookId
    hook_condition: Condition
    hook_action: Action
    hook_stats: Stats
    hook_meta: Metadata
    hook_specificity: Specificity


@dataclass(frozen=True)
class HookMatch:
    match_hook: Hook
    match_context: Context
    match_cost: Cost


@dataclass(frozen=True)
class Policy:
    policy_minimize_input: bool
    policy_success_weight: float
    policy_max_cascade_depth: int


@dataclass(frozen=True)
class HookStore:
    hooks: dict[HookId, Hook] = field(default_factory=dict)
    indices: dict[str, list[HookId]] = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    snapshot_context: Context
    snapshot_time: datetime
    snapshot_id: str


@dataclass(frozen=True)
class UserInput:
    input_actions: tuple[Op, ...]
    input_corrections: tuple[str, ...]
    input_time: datetime


class Equiv(str, Enum):
    EQUIVALENT = "Equivalent"
    NOT_EQUIVALENT = "NotEquivalent"
