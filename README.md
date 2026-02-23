# knowledgehook

`knowledgehook` is a pure, deterministic Python kernel for defining, matching, selecting, and learning reusable automation hooks.

The package is designed for predictable behavior:

- no network calls
- no UI automation side effects
- no hidden state

All operations are regular Python functions over typed dataclasses.

## Research Context: Subjective Thermo-Currency

This repository implements the practical **algebra of knowledge hooks** used as a kernel for 0-input / 0-energy style automation flows, and as a computational substrate for Subjective Thermo-Currency style systems.

Related paper (in progress):

- **Subjective Thermo-Currency (TechRxiv draft PDF)**: https://cdn.subjectivetechnologies.com/downloads/stc_in_progress/subjective_thermo_currency_techrxiv.pdf

In this framing, a hook is a compact unit of operational knowledge:

- **Condition** (`when`) over context
- **Action plan** (`what`) as explicit operations
- **Stats/metadata** (`how well` and `where from`)

The algebra composes these units while preserving determinism and auditability.

## Algebra of Knowledge Hooks

The kernel exposes a small, closed algebra over hooks and contexts:

- **Activation** (`activate`): evaluate condition predicates against a context to produce candidate matches.
- **Selection** (`prioritize`): choose the best candidate with deterministic ordering (lower estimated input/cost first, then higher success score).
- **Execution** (`execute`): interpret an action plan to produce a new context and outcome plan.
- **Rollback** (`rollback` / `interpret_rollback`): invert operations to recover a prior state trajectory.
- **Learning** (`learn_delta`): infer a new hook from before/after snapshots plus user actions.
- **Composition** (`compose_nested`, `compose_flat`, `combine_hooks`): build higher-order hooks from existing ones.
- **Refinement** (`refine`): specialize a hook by conjunction with additional constraints.
- **Equivalence & normalization** (`equivalent`, condition normalization): compare hooks modulo logical normalization.
- **Policy-limited propagation** (`cascade`): run bounded follow-on activations.
- **Score updates** (`negative_rl_update`, `update_stats`): update reliability estimates from corrections.

At the logical layer, conditions form a boolean algebra (AND/OR/NOT, normalization, De Morgan compatibility). At the operational layer, plans form a compositional action algebra with explicit cost and rollback semantics.

## Requirements

- Python 3.12+

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Quick Start

Run the demo CLI:

```bash
python -m knowledgehook.demo
```

The demo prints sections for:

- predefined hook activation
- learning from snapshot delta
- cascading behavior
- rollback behavior
- hook composition

## Run Tests

```bash
pytest
```

## Package Layout

- `knowledgehook/types.py` - core dataclasses and AST nodes
- `knowledgehook/semantics.py` - condition evaluation and normalization
- `knowledgehook/algebra.py` - activation, prioritization, execution, learning, composition
- `knowledgehook/store.py` - pure store/index operations
- `knowledgehook/examples.py` - sample hooks and scenarios
- `knowledgehook/demo.py` - CLI demonstration
- `tests/` - property tests and smoke tests

## Core Concepts

- **Condition AST**: boolean predicates over `Context`
- **Hook**: `condition + action + stats + metadata + specificity`
- **OutcomePlan**: operations, rollback plan, and estimated cost
- **Policy**: deterministic selection rules for matched hooks
- **Learning**: `learn_delta` creates a new learned hook from snapshots and user actions

## Determinism and Purity

`knowledgehook` stays side-effect free by returning plans and transformed contexts rather than performing external automation directly.
