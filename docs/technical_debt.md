# Technical Debt

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
