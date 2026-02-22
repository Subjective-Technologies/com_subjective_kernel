# knowledgehook

`knowledgehook` is a pure, deterministic Python kernel for defining, matching, selecting, and learning reusable automation hooks.

The package is designed for predictable behavior:

- no network calls
- no UI automation side effects
- no hidden state

All operations are regular Python functions over typed dataclasses.

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
