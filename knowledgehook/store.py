from __future__ import annotations

from .semantics import normalize_condition
from .types import Alpha, Condition, Context, Cost, Hook, HookId, HookStore, Policy, Score, Specificity


def default_policy() -> Policy:
    return Policy(policy_minimize_input=True, policy_success_weight=1.0, policy_max_cascade_depth=3)


def empty_store() -> HookStore:
    return HookStore(hooks={}, indices={})


def condition_key(condition: Condition) -> str:
    return repr(normalize_condition(condition))


def insert_hook(hook: Hook, store: HookStore) -> HookStore:
    hooks = dict(store.hooks)
    hooks[hook.hook_id] = hook
    indices = {k: list(v) for k, v in store.indices.items()}
    key = condition_key(hook.hook_condition)
    indices.setdefault(key, []).append(hook.hook_id)
    return HookStore(hooks=hooks, indices=indices)


def lookup_hook(hook_id: HookId, store: HookStore) -> Hook | None:
    return store.hooks.get(hook_id)


def delete_hook(hook_id: HookId, store: HookStore) -> HookStore:
    hooks = dict(store.hooks)
    hooks.pop(hook_id, None)
    # Matches Haskell TODO semantics: do not clean indices.
    return HookStore(hooks=hooks, indices={k: list(v) for k, v in store.indices.items()})


def update_hook(hook: Hook, store: HookStore) -> HookStore:
    return insert_hook(hook, delete_hook(hook.hook_id, store))


def mk_alpha(x: float) -> Alpha | None:
    if 0.0 < x < 1.0:
        return x
    return None


def mk_score(x: float) -> Score | None:
    if 0.0 <= x <= 1.0:
        return x
    return None


def mk_cost(x: float) -> Cost | None:
    if x >= 0.0:
        return x
    return None


def mk_specificity(x: float) -> Specificity | None:
    if x >= 0.0:
        return x
    return None
