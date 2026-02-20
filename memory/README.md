# Memory Subsystem

This package implements memory as the core product surface.

## Types

- Context (in-RAM session buffer)
- Episodic (`episodes`)
- Semantic (`beliefs`)
- Procedural (`skills`)
- Goal (`goals`)
- Self-model (`self_model`)
- Uncertainty ledger (`hypotheses`)

## Key Flows

- Every control-loop step logs episodes.
- Retrieval blends lexical, recency, confidence, and optional vector signals.
- Consolidation (`memory/consolidation`) turns episodes into beliefs and resolves contradictions.
