# LN09k — Restore live founders after shelter collapse

Owner approved the shelter restore proposal following LN09j, base `815097a`.
The live attachment validator must recognize previously composed and destroyed
camp-owned shelters. Preserve the exact maintenance policy/state, marker and
housing relationship validation. The consequence manager owns collapse and
terminal state, and the existing capacity predicate excludes destroyed shelters.
A destroyed shelter never receives new attachments. Leave recorded composition,
active storage selection, world and archive formats, authority, NPC context,
provider contracts, parser, gateway, and acceptance criteria unchanged.

## Files and steps

- [ ] RED and GREEN in `tests/test_runtime_founders_feedback.py`. Drive ordinary
  maintenance collapse. Restore a mixed live and destroyed shelter snapshot
  byte-for-byte, continue an ordinary tick, and verify history, capacity and
  lack of destroyed-shelter upkeep. Reject damaged history without repair.
- [ ] Change only `src/living_world/founders/setup.py` in production. Pass the
  existing live mode into both attachment calls. Validate live-mode destroyed
  owned constructed shelters alongside active shelters; keep active storage
  selection as it was. Enforce complete historical attachment shape.
- [ ] Independently review the scoped diff, then prove exact offline replay of
  the retained native source through checkpoint 14 in a separate catalog copy.
  Run full task and merged gates, including all examples and whitespace.
- [ ] Run bounded real provider acceptance under the unchanged criteria after
  the replay proof. Preserve the source archive, other branches and owner edit.

The saved prompt and report, CHANGELOG, project journal, backlog, and continuation
brief are task documentation. No other production or test files are authorized.
