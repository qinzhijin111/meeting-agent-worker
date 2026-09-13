
# Week 6 Note Taker Test Cases

These tests use synthetic/demo meeting content only.

## Test Case 1 - Short Meeting With One Speaker

### Input

Speaker: Alice

- We decided to release the dashboard on Friday.
- I will prepare the release checklist by Thursday.
- We still need to decide who will monitor the deployment.

### Expected Notes

Summary:
The team discussed the dashboard release and related preparation.

Decisions:
- Release the dashboard on Friday.

Action Items:
- Prepare the release checklist.
  - Owner: Alice
  - Due date: Thursday

Open Questions:
- Who will monitor the deployment?

Expected status:

`ready`

### Actual Notes

Replace this section with the actual output produced by the Note Taker.

Summary:

...

Decisions:

...

Action Items:

...

Open Questions:

...

Actual status:

`...`

### Result

PASS / FAIL


## Test Case 2 - Three-Speaker Meeting

### Input

Alice:
We decided to use the staging environment for Monday's demo.

Bob:
I will prepare the demo slides by Sunday.

Carol:
Who will run the backup demo if staging is unavailable?

### Expected Notes

Decisions:
- Use the staging environment for Monday's demo.

Action Items:
- Prepare the demo slides.
  - Owner: Bob
  - Due date: Sunday

Open Questions:
- Who will run the backup demo if staging is unavailable?

Expected status:

`ready`

### Actual Notes

Summary:

...

Decisions:

...

Action Items:

...

Open Questions:

...

Actual status:

`...`

### Result

PASS / FAIL


## Test Case 3 - No Speech

### Input

No participant speech.

### Expected Notes

Summary:

`No meaningful speech was captured.`

Decisions:

`[]`

Action Items:

`[]`

Open Questions:

`[]`

Expected status:

`ready`

### Actual Notes

Summary:

...

Decisions:

...

Action Items:

...

Open Questions:

...

Actual status:

`...`

### Result

PASS / FAIL


## Failure-Recovery Exploration

A controlled note-generation failure was triggered after transcript
segments had already been collected.

Expected result:

- Existing transcript-derived work is not silently discarded.
- Status becomes `partial`.
- Human meeting continues normally.
- An understandable error is stored/displayed.

Actual result:

...

Result:

PASS / FAIL / KNOWN LIMITATION
