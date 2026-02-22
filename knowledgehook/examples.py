from __future__ import annotations

from datetime import datetime, timedelta

from .algebra import activate, execute, update_stats
from .semantics import andP, hasText, inApp
from .store import default_policy, empty_store, insert_hook
from .types import (
    Action,
    ClickElement,
    Context,
    Cost,
    Feature,
    Hook,
    Metadata,
    NumericValue,
    OpenApp,
    OutcomePlan,
    RollbackPlan,
    Score,
    SendKeys,
    Snapshot,
    Specificity,
    Stats,
    TextValue,
    TypeText,
    UserInput,
    Wait,
)


def example_context(current_time: datetime) -> Context:
    return Context(
        features={
            Feature("current_text", "text"): TextValue("Schedule a meeting for tomorrow"),
            Feature("window_title", "ui"): TextValue("Email - Inbox"),
            Feature("cursor_position", "ui"): NumericValue(42),
        },
        time=current_time,
        app="email",
    )


def example_seed_hook(current_time: datetime) -> Hook:
    return Hook(
        hook_id="seed_email_reply",
        hook_condition=andP(inApp("email"), hasText("meeting")),
        hook_action=Action(
            action_plan=OutcomePlan(
                plan_ops=(ClickElement("reply_button"), TypeText("I'll be there!"), ClickElement("send_button")),
                plan_rollback=RollbackPlan(
                    rollback_ops=(ClickElement("undo_send"), ClickElement("delete_draft")),
                    rollback_context=example_context(current_time),
                ),
                plan_cost=3.0,
            ),
            action_description="Quick meeting reply",
        ),
        hook_stats=Stats(stats_success=0.8, stats_uses=15, stats_corrections=2),
        hook_meta=Metadata(
            meta_created=current_time,
            meta_modified=current_time,
            meta_source="predefined",
            meta_tags=("email", "meeting"),
        ),
        hook_specificity=0.7,
    )


def example_learned_hook(current_time: datetime) -> Hook:
    return Hook(
        hook_id="learned_calendar_create",
        hook_condition=andP(inApp("calendar"), hasText("appointment")),
        hook_action=Action(
            action_plan=OutcomePlan(
                plan_ops=(ClickElement("new_event"), TypeText("Doctor Appointment"), ClickElement("save")),
                plan_rollback=RollbackPlan(rollback_ops=(ClickElement("delete_event"),), rollback_context=example_context(current_time)),
                plan_cost=2.5,
            ),
            action_description="Create calendar event",
        ),
        hook_stats=Stats(stats_success=0.6, stats_uses=3, stats_corrections=1),
        hook_meta=Metadata(
            meta_created=current_time,
            meta_modified=current_time,
            meta_source="learned",
            meta_tags=("calendar",),
        ),
        hook_specificity=0.5,
    )


def example_delta_scenario(current_time: datetime) -> tuple[Snapshot, Snapshot, UserInput]:
    before_ctx = example_context(current_time)
    after_ctx = Context(
        features={**before_ctx.features, Feature("new_event", "ui"): TextValue("Meeting with Bob")},
        time=before_ctx.time,
        app="calendar",
    )
    before = Snapshot(snapshot_context=before_ctx, snapshot_time=current_time, snapshot_id="snapshot_before")
    after = Snapshot(snapshot_context=after_ctx, snapshot_time=current_time + timedelta(seconds=60), snapshot_id="snapshot_after")
    user_input = UserInput(
        input_actions=(OpenApp("calendar"), ClickElement("new_event"), TypeText("Meeting with Bob"), ClickElement("save")),
        input_corrections=("Had to manually open calendar",),
        input_time=current_time + timedelta(seconds=30),
    )
    return before, after, user_input


def example_cascading_pair(current_time: datetime) -> tuple[Hook, Hook, Context]:
    hook1 = Hook(
        hook_id="send_email",
        hook_condition=hasText("send email"),
        hook_action=Action(
            action_plan=OutcomePlan(
                plan_ops=(TypeText("Email sent successfully!"),),
                plan_rollback=RollbackPlan(rollback_ops=(), rollback_context=example_context(current_time)),
                plan_cost=1.0,
            ),
            action_description="Send email",
        ),
        hook_stats=Stats(stats_success=0.9, stats_uses=10, stats_corrections=0),
        hook_meta=Metadata(current_time, current_time, "predefined", ("email",)),
        hook_specificity=0.4,
    )
    hook2 = Hook(
        hook_id="log_activity",
        hook_condition=hasText("Email sent successfully!"),
        hook_action=Action(
            action_plan=OutcomePlan(
                plan_ops=(OpenApp("logger"), TypeText("Email activity logged")),
                plan_rollback=RollbackPlan(rollback_ops=(), rollback_context=example_context(current_time)),
                plan_cost=0.5,
            ),
            action_description="Log email activity",
        ),
        hook_stats=Stats(stats_success=0.95, stats_uses=8, stats_corrections=0),
        hook_meta=Metadata(current_time, current_time, "predefined", ("logging",)),
        hook_specificity=0.6,
    )
    ctx = Context(
        features={Feature("user_intent", "text"): TextValue("send email to client")},
        time=current_time,
        app="email",
    )
    return hook1, hook2, ctx


def example_rollback_scenario(current_time: datetime) -> tuple[Action, Context]:
    action = Action(
        action_plan=OutcomePlan(
            plan_ops=(OpenApp("notepad"), TypeText("This is a test note"), ClickElement("save_as")),
            plan_rollback=RollbackPlan(
                rollback_ops=(ClickElement("delete_file"), OpenApp("previous_app")),
                rollback_context=example_context(current_time),
            ),
            plan_cost=2.0,
        ),
        action_description="Create and save note",
    )
    return action, example_context(current_time)


def example_composition_pair(current_time: datetime) -> tuple[Hook, Hook]:
    hook1 = Hook(
        hook_id="copy_text",
        hook_condition=hasText("copy this"),
        hook_action=Action(
            action_plan=OutcomePlan(
                plan_ops=(SendKeys("Ctrl+C"),),
                plan_rollback=RollbackPlan(rollback_ops=(), rollback_context=example_context(current_time)),
                plan_cost=0.1,
            ),
            action_description="Copy selected text",
        ),
        hook_stats=Stats(stats_success=0.95, stats_uses=100, stats_corrections=1),
        hook_meta=Metadata(current_time, current_time, "predefined", ("clipboard",)),
        hook_specificity=0.3,
    )
    hook2 = Hook(
        hook_id="paste_text",
        hook_condition=hasText("paste here"),
        hook_action=Action(
            action_plan=OutcomePlan(
                plan_ops=(SendKeys("Ctrl+V"),),
                plan_rollback=RollbackPlan(rollback_ops=(SendKeys("Ctrl+Z"),), rollback_context=example_context(current_time)),
                plan_cost=0.1,
            ),
            action_description="Paste clipboard content",
        ),
        hook_stats=Stats(stats_success=0.92, stats_uses=80, stats_corrections=3),
        hook_meta=Metadata(current_time, current_time, "predefined", ("clipboard",)),
        hook_specificity=0.3,
    )
    return hook1, hook2


def create_sample_store(current_time: datetime):
    store = empty_store()
    store = insert_hook(example_seed_hook(current_time), store)
    store = insert_hook(example_learned_hook(current_time), store)
    return store


def demonstrate_workflow(current_time: datetime) -> tuple[int, str | None, float | None]:
    store = create_sample_store(current_time)
    ctx = example_context(current_time)
    matches = activate(store, ctx)
    if not matches:
        return 0, None, None
    chosen = min(matches, key=lambda m: (m.match_cost, -m.match_hook.hook_stats.stats_success))
    outcome = execute(chosen.match_hook, ctx)
    updated = update_stats(0.1, chosen.match_hook, outcome.outcome_correction)
    return len(matches), chosen.match_hook.hook_id, updated.hook_stats.stats_success
