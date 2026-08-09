# Development Rules

For every commit:

2.  Review the proposed plan here before implementation when the change
    is architectural.
3.  Implement things in incremental batches while testing and running examples one batch at a time.
4.  Keep changes limited within each batch.
5.  Run `make` after each batch or logical group of batches and make sure everything works.
6.  Review the diff before committing.
7.  Update `CHANGELOG.md` and `docs/project_journal.md` before the
    commit.
8.  Update `docs/backlog.md` before the commit, removing stale items and
    adding future work that must not be lost.
9.  Do not replace existing architecture merely to make a new feature
    easier.
10. Preserve the distinction between:
    -   authoritative simulation state
    -   perception
    -   cognition
    -   LLM reasoning
10. The NPC LLMs must never become the authoritative source of world truth.