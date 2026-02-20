# Security and Governance

## Default Posture

The system starts in safe mode with all risky actions disabled by default:

- shell execution disabled
- OS automation disabled
- network disabled
- workspace write boundary enforced
- budget cap set to zero

For host safety, run the operator in a container by default (`Dockerfile`, `docker-compose.yml`).

## Enforcement Path

All actions go through:

1. `governance.permission_engine.PermissionEngine` for policy gates.
2. `governance.risk_scoring.score_action_risk` for heuristic risk.
3. `executor.safe_runner.SafeRunner` for final allow/block and auditing.

## Audit Trail

- JSONL log file at `logs/audit.jsonl`
- includes timestamp, action, tool, hashed inputs, outcome, and reason

## Rollback

`executor.rollback_manager.RollbackManager` stores workspace checkpoints and restores files on rollback.

## Non-Goals

- No autonomous destructive operations.
- No implicit cloud deployment or payments.
- No hidden network calls in default configuration.
