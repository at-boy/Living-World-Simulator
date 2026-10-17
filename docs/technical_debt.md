# Technical Debt

## v0.6 candidate closeout checkpoint

Task23 is reviewed and integrated as58b6ba7. Task24 metadata/docs preparation
introduces no runtime change or newly established architecture debt. Whole-milestone targeted code review and all four scoped corrections passed;
final candidate review and current release gates remain in the
[closeout report](subagent_execution_plan/v0_6/24_v06_release_closeout-report.md).
This is not a claim that future capabilities or all possible defects are resolved.
Generic scenario authoring, live-model strategy validation, legacy replay without
label bindings, stage templates/demotion and automatic stage perception remain
backlog scope; dense spatial labels retain the accessible list fallback.

This document tracks known implementation gaps between the current
codebase and the intended architecture.

It is **not** a bug tracker and **not** a feature backlog.

-   **Backlog** contains future capabilities that have not been started.
-   **Technical Debt** contains work that has already been designed or
    partially implemented but has not yet been brought into alignment
    with the architecture.

Each item should include enough context to explain **why** it exists and
**what** will resolve it.

When an item is completed, it should be removed from this document as
part of the same pull request.

------------------------------------------------------------------------

# High Priority

Task 24a addresses four concrete v0.6 release-audit findings in its isolated
correction wave; independent review and task/merged root validation passed at
1416tests/10existing skips,76Chrome and examples001–039. They
are tracked by the authorized Task 24a plan/report, rather than deferred debt.
Existing EventManager private allocation can retain gaps after an exceptional
recording call; Task 24a preserves that behavior and makes no gapless retry-event
claim. Reservation state/history/counter rollback remains required.

There are no active high-priority technical-debt entries at the v0.5 closeout.
The former entity lifecycle, relationship lifecycle, immutable history,
repository, and baseline-audit entries were removed only after their recorded
resolution criteria were verified by implementation and tests.

------------------------------------------------------------------------

# Notes

Technical debt should decrease over time.

If this document continually grows, it is a sign that architectural
decisions are not being completed before new work begins.

The goal is to keep this document short, current, and actionable.
