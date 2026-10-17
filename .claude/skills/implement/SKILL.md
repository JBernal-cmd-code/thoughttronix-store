---
name: implement
description: Implement one approved phase from a PRD and plan using feedback loops.
argument-hint: "@prd/<feature>.md @plans/<feature>.md implement phase <N>"
disable-model-invocation: true
---

# Implement

## 1. Understand the Phase

Read the referenced PRD and plan. Explore the codebase to understand the relevant files,
patterns, and conventions. If the request does not identify a phase, ask which one.

Implement only that phase. Do not begin the next one.

## 2. Implement the Phase

Run the tdd skill and follow it. Build everything else the project’s normal way.

## 3. Run Feedback Loops

Run the test suite, linter, formatter, and any other checks. Fix failures and re-run until everything passes.

## 4. Manual Verification

Answer "How do I verify this phase or feature manually in the browser?" Then stop and wait for the user's confirmation. The phase is not finished until the user confirms it passed.

## 5. Finish the Phase

Update PROMPTS.md in its format, commit, push