# How to Write a System Use Case

| Field | Value |
| --- | --- |
| Audience | Test engineers, product owners, AI agents |
| Prerequisites | Familiarity with the system under test |
| Time estimate | 30–60 min per use case |

## What Is a System Use Case?

A system use case captures **what the system must do** from the perspective
of an actor interacting with it. It is a requirement — not a test, not a
design, and not an implementation plan.

The format follows Alistair Cockburn's *Writing Effective Use Cases*
template: a structured description of a goal, the actors involved, the
conditions before and after, and a step-by-step main success scenario with
extensions for failure and variation paths.

## Why Use Cases Matter

Use cases are **Layer 0** in the
[five-layer architecture](boardfarm-five-layer-model.md). They sit above all
test automation code and serve three purposes:

1. **Requirements capture** — document what the system should do before
   writing any test code
2. **Test driver** — each use case directly drives one or more test
   scenarios at Layer 1 (Gherkin features / Robot test cases)
3. **Traceability anchor** — the use case ID links requirements to test
   specifications, step definitions, and Boardfarm use case code

```
Layer 0: System Use Case  ← you are here
    │ drives
    ▼
Layer 1: Test Definition  (Gherkin / Robot)
    │
    ▼
Layer 2: Step Defs / Keywords  (thin wrappers)
    │
    ▼
Layer 3: Boardfarm Use Cases  (business logic, via parameter)
    │
    ▼
Layer 4: Device Templates  (device contracts)
```

A use case says *"the operator reboots the CPE via the ACS"*. It does not
say *how* (REST API, GUI, CLI) — that is decided at Layer 3 through the
`via` parameter.

## When to Write a Use Case

Write a use case when:

- A new feature or behaviour needs to be tested
- An existing behaviour is not yet formally documented
- You need to clarify stakeholder expectations before automating
- You want to ensure traceability from requirement to test code

Do **not** write a use case for:

- Internal implementation details (those belong in design documents)
- Low-level API specifications (those belong in API references)
- Test infrastructure setup (those belong in how-to guides)

## How to Write One

### 1. Start with the Goal

Write a single sentence describing what the primary actor is trying to
accomplish. Use a verb phrase from the actor's perspective:

- "Remotely reboot the CPE device to restore connectivity"
- "Measure video conference quality under WAN degradation"
- "Establish an encrypted overlay tunnel between sites"

### 2. Choose the Level

| Level | Scope | Example |
|---|---|---|
| **Summary** | Strategic; spans multiple user-goals | "Manage CPE fleet via ACS" |
| **User-goal** | One sitting, one goal (most common) | "Reboot a CPE via ACS" |
| **Subfunction** | A step extracted for reuse | "Verify CPE sends Inform message" |

Most use cases are **User-goal** level.

### 3. Fill in the Template

Copy the [Use Case Template](use-case-template.md) and fill in each section.
The sections are:

| Section                            | What to write                                                          |
| ---------------------------------- | ---------------------------------------------------------------------- |
| **Goal**                           | Verb phrase — what the actor wants                                     |
| **Scope**                          | The system boundary ("the E2E system including ACS, CPE, and network") |
| **Primary Actor**                  | Who initiates the action (this can be a person or a system)            |
| **Stakeholders**                   | Who else cares and why (this can be a person or a system)              |
| **Level**                          | Summary, User-goal, or Subfunction                                    |
| **Preconditions**                  | What must be true before the use case starts                           |
| **Minimal Guarantees**             | What is always true, even if the use case fails                        |
| **Success Guarantees**             | What is true when the use case succeeds                                |
| **Trigger**                        | What starts it (actor action or time event)                            |
| **Main Success Scenario**          | Numbered steps from trigger to goal delivery                           |
| **Extensions**                     | Branching conditions referencing main scenario step numbers            |
| **Technology and Data Variations** | Variations that may require separate test paths                        |
| **Traceability**                   | Links to test specs, step defs, and Boardfarm use case code            |
| **Related Information**            | Links to design docs, ADRs, other use cases                            |

### 4. Write the Main Success Scenario

Each step should be an **observable interaction** between an actor and the
system. Avoid implementation details:

```
1. The operator initiates a reboot command via the ACS.
2. The ACS creates a reboot task for the CPE.
3. The ACS sends a connection request to the CPE.
4. The CPE receives the connection request and initiates a session.
5. The CPE sends an Inform message to the ACS.
6. The ACS issues the Reboot RPC to the CPE.
7. The CPE executes the reboot command.
...
```

Each step becomes a candidate for a **verifiable** Gherkin step or Robot keyword at
Layer 1.

### 5. Add Extensions

Extensions branch from a specific step in the main scenario. Use the
step number as a prefix:

```
- 3a. CPE not connected when reboot requested:
  1. The ACS queues the Reboot RPC as a pending task.
  2. When the CPE comes online, it connects to the ACS.
  3. The ACS issues the queued Reboot RPC.
  4. Continue from step 7 of the main success scenario.
```

Avoid nesting extensions more than two levels deep. If an extension is
complex, extract it as a separate sub-function use case and reference it.

### 6. Fill in Traceability

The traceability section links the use case to its automated test
artifacts:

| Artifact | pytest-bdd | Robot Framework |
| --- | --- | --- |
| Test specification | `tests/features/reboot.feature` | `robot/tests/reboot.robot` |
| Step / keyword impl | `tests/step_defs/acs_steps.py` | `robot/libraries/acs_keywords.py` |
| Use case code | `boardfarm3/use_cases/acs.py` | `boardfarm3/use_cases/acs.py` |

This is how you trace a requirement through to its implementation.

## Naming and Filing

- **Filename**: `UC-{DOMAIN}-{NNN} {Title}.md`
- **Location**: `requirements/`
- **ID format**: `UC-{DOMAIN}-{NNN}` (e.g., `UC-ACS-GUI-01`,
  `UC-SDWAN-03`, `UC-12347`)

The domain prefix groups related use cases. Existing domains include
`ACS`, `SDWAN`, and legacy numeric IDs.

## Examples

The `requirements/` directory contains production use cases:

| Use Case | Level | Domain |
|---|---|---|
| [UC-12347 Remote CPE Reboot](../../requirements/UC-12347%20remote%20cpe%20reboot.md) | User-goal | ACS/CPE |
| [UC-ACS-GUI-01 ACS GUI Device Management](../../requirements/UC-ACS-GUI-01%20ACS%20GUI%20Device%20Management.md) | User-goal | ACS GUI |
| [UC-SDWAN-01 WAN Failover](../../requirements/UC-SDWAN-01%20WAN%20Failover%20Maintains%20Application%20Continuity.md) | User-goal | SD-WAN |
| [UC-SDWAN-03 Video Conference Quality](../../requirements/UC-SDWAN-03%20Video%20Conference%20Quality%20Under%20WAN%20Degradation.md) | User-goal | SD-WAN |
| [UC-12348 One-Way Call](../../requirements/UC-12348%20User%20makes%20a%20one-way%20call.md) | User-goal | Voice |

## Related Documentation

| Document | Description |
|---|---|
| [Use Case Template](use-case-template.md) | Blank copyable form |
| [Boardfarm Five-Layer Model](boardfarm-five-layer-model.md) | How use cases fit into the architecture |
| [Boardfarm Test Automation Architecture](boardfarm-five-layer-model.md#writing-new-test-scenarios) | Step-by-step process for turning use cases into tests |
