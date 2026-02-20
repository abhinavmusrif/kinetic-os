# Memory Design

## Memory Types

- Context: short-term session buffer (RAM ring buffer).
- Episodic: timestamped execution and observation events.
- Semantic: beliefs and preferences with confidence + lifecycle status.
- Procedural: skills/workflows, constraints, and failure modes.
- Goals: active goals and progress state.
- Self-model: capabilities/limitations and reliability scores.
- Uncertainty ledger: hypotheses and verification plans.

## Episodic -> Semantic Flow

1. Episodes are created during every control-loop step.
2. Replay engine mines episodes for candidate beliefs and skill updates.
3. Beliefs are inserted as `status=proposed` with uncertainty-aware confidence.
4. Contradiction finder marks conflicting beliefs as `disputed`.
5. Forgetting policy decays/prunes low-salience old episodes while preserving evidence hashes.

## Confidence and Conflict

- Confidence is modeled as `float [0,1]`.
- New claims default below certainty unless verified.
- Conflicting claims link via `conflicts_with_ids`.
- Disputed claims remain queryable for traceability.

## Retrieval

Hybrid score combines:

- lexical overlap
- optional vector similarity
- recency
- confidence
- goal relevance

This supports conservative memory injection into prompts.
