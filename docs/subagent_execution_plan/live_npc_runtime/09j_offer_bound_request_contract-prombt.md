# Saved worker prompt — LN09j

Read AGENTS.md and exact 09j_offer_bound_request_contract.md first. Implement
the approved opt-in contract only, using TDD and the exact allowed paths.
Keep the parser, gateway, all acceptance criteria and both old wire formats
unchanged. Root has already used Serena on the feature worktree to trace
request_contract_format references and provider config. Serena server is shared;
do not activate a different project or change config during this task.
Use task24 venv, PYTHONPATH=src, scoped pytest/Ruff/Black. Owned fake HTTP
fixtures only; no native models, dependencies, Git mutations, other worktrees
or subagents. Preserve existing tests. Record RED/GREEN and source scope in
matching -report.md, then freeze. Root owns acceptance, full gates and Git.
