## Problem

What went wrong, where, with the evidence.

## Fix

What changed and why this is the right place for it.

## Tests

Which tests fail before the change and pass after it, and the full suite's summary line.

## Adversarial review

Required when this pull request changes `pub-check/oasis_pub_check.py`; the
`Gate change review` check reads this section. An independent reviewer (not the
author) is told to construct an input on which the change hides a real defect or
raises a false one. List each counterexample tried and, for each, the test this
pull request adds or modifies that pins it:

- counterexample: ... pinned by `tests/test_example.py::test_the_counterexample`

For a pure refactor or a message-text change, write `not applicable: <reason>`
instead.
