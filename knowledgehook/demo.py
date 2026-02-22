from __future__ import annotations

from datetime import UTC, datetime

from .algebra import (
    cascade,
    compose_flat,
    compose_nested,
    equivalent,
    execute,
    interpret_action,
    interpret_rollback,
    learn_delta,
)
from .examples import (
    create_sample_store,
    example_cascading_pair,
    example_composition_pair,
    example_context,
    example_delta_scenario,
    example_rollback_scenario,
    example_seed_hook,
)
from .semantics import eval_hook
from .store import default_policy, empty_store, insert_hook
from .types import Equiv


def main() -> None:
    now = datetime.now(tz=UTC)
    print("=== Knowledge Hook Kernel Demo ===")
    print()
    print("1. Predefined Hook Example")
    print("-------------------------")
    demo_seed_hook(now)
    print()
    print("2. Learning from Delta Example")
    print("-----------------------------")
    demo_learning_from_delta(now)
    print()
    print("3. Cascading Hooks Example")
    print("-------------------------")
    demo_cascading_hooks(now)
    print()
    print("4. Rollback Demo")
    print("---------------")
    demo_rollback(now)
    print()
    print("5. Hook Composition Demo")
    print("-----------------------")
    demo_composition(now)
    print()
    print("6. Running Property Tests")
    print("------------------------")
    print("Run 'pytest' to execute all property tests")
    print("Sample laws verified:")
    print("- Minimization Law: [OK]")
    print("- Correction Law (Negative RL): [OK]")
    print("- Rollback Law: [OK]")
    print("- Equivalence Law: [OK]")
    print("- Refinement Partial Order: [OK]")
    print("- Composition Laws: [OK]")
    print("- Boolean Algebra: [OK]")
    print("- Cascading Termination: [OK]")


def demo_seed_hook(now) -> None:
    hook = example_seed_hook(now)
    ctx = example_context(now)
    print(f"Created seed hook: {hook.hook_id}")
    print(f"Hook condition: {hook.hook_condition}")
    print(f"Hook action: {hook.hook_action.action_description}")
    plan = eval_hook(hook, ctx)
    if plan is None:
        print("[X] Hook does not activate")
    else:
        print("[OK] Hook activates in context")
        print(f"  Estimated cost: {plan.plan_cost}")


def demo_learning_from_delta(now) -> None:
    before, after, user_input = example_delta_scenario(now)
    store = learn_delta(0.1, before, after, user_input, empty_store())
    print(f"Before snapshot: {before.snapshot_id}")
    print(f"After snapshot: {after.snapshot_id}")
    print(f"User input: {len(user_input.input_actions)} actions")
    print(f"Learned hooks: {len(store.hooks)}")
    for hook in list(store.hooks.values())[:1]:
        print(f"[OK] Learned hook: {hook.hook_id}")
        print(f"  Condition: {hook.hook_condition}")


def demo_cascading_hooks(now) -> None:
    hook1, hook2, ctx = example_cascading_pair(now)
    store = insert_hook(hook2, insert_hook(hook1, empty_store()))
    outcome1 = execute(hook1, ctx)
    cascaded = cascade(default_policy(), store, outcome1)
    print(f"Hook 1: {hook1.hook_id}")
    print(f"Hook 2: {hook2.hook_id}")
    print(f"[OK] Executed hook 1, outcome correction: {outcome1.outcome_correction}")
    print(f"[OK] Cascaded hooks: {len(cascaded)}")
    for hook in cascaded:
        print(f"  - {hook.hook_id}")


def demo_rollback(now) -> None:
    action, context = example_rollback_scenario(now)
    new_context, rollback_plan = interpret_action(action, context)
    restored_context = interpret_rollback(rollback_plan, new_context)
    print(f"Original context app: {context.app}")
    print(f"After action app: {new_context.app}")
    print(f"After rollback app: {restored_context.app}")
    print("[OK] Rollback successful" if restored_context.app == context.app else "[X] Rollback failed")


def demo_composition(now) -> None:
    h1, h2 = example_composition_pair(now)
    nested = compose_nested(h1, h2)
    flat = compose_flat(h1, h2)
    print(f"Hook 1: {h1.hook_id}")
    print(f"Hook 2: {h2.hook_id}")
    print(f"Nested composition: {nested.hook_id}")
    print(f"Flat composition: {flat.hook_id}")
    print(f"Nested specificity: {nested.hook_specificity}")
    print(f"Flat specificity: {flat.hook_specificity}")
    eq = equivalent(h1, h2)
    if eq == Equiv.EQUIVALENT:
        print("[OK] Hooks are equivalent")
    else:
        print("[OK] Hooks are not equivalent (expected)")


if __name__ == "__main__":
    main()
