# Productization Checklist

This checklist covers the smaller gated work that should happen after the major Phase 2 integrations are complete.

It uses checklist format instead of a full mini roadmap because these steps are narrower and should not interrupt the main integration sequence.

## Use rule

- do not start this checklist until the Phase 2 integration roadmaps are completed
- complete each checkpoint in order
- add a short note under each checkpoint when it is done

## Checkpoint 1: Windows packaging path

Goal:

- produce a repeatable packaged Windows build path for the PySide app

Done when:

- the repo documents the packaging command path
- the packaged app can launch on a clean test run
- resource and startup issues are addressed

Completion note:

- summary:
- proof added to repo:

## Checkpoint 2: Installer and first-run experience

Goal:

- make the Windows app feel installable and testable like a product

Done when:

- there is an installer or installer-ready distribution path
- first-run messaging and required local prerequisites are documented and visible

Completion note:

- summary:
- proof added to repo:

## Checkpoint 3: Trust and recovery polish

Goal:

- tighten the most important failure, retry, and recovery edges

Done when:

- the main local failure modes have clear user-facing explanations
- the GUI can guide the user toward recovery instead of only showing raw errors

Completion note:

- summary:
- proof added to repo:
