# Bug Report — Pretty Good AI Voice Agent

Findings from testing Pretty Good AI's phone agent ("Pivot Point
Orthopedics" demo line) at +1-805-439-8008, across 10 real recorded calls
covering scheduling, rescheduling, cancellation, medication refills,
hours/location/insurance questions, and edge cases. Call recordings and
transcripts referenced below are in `calls/`.

---

## Bug 1: Repeated vague deflection instead of answering a direct question

**Severity:** Medium
**Scenario:** Hours inquiry (initial exploratory call, pre-dates the
scenario config system)

When asked directly for the exact opening time, the agent repeatedly
responded with a vague restatement ("the clinic is open now") instead of a
specific time. The caller had to rephrase the same question three times
before the agent acknowledged it didn't have the information and offered to
check.

**Impact:** A real caller with a simple, specific question (what time do you
open) would need to be unusually persistent to get a straight answer, or
would give up with no answer at all.

---

## Bug 2: Explicit admission of a real information gap

**Severity:** Medium
**Scenario:** `hours_inquiry`

In a later, transcript-logged call, the agent explicitly stated: *"I don't
have the exact opening time for the office."* This is a direct, unambiguous
confirmation that basic operating-hours information — something a real
orthopedic office's phone system should have readily available — is missing
or inaccessible to the agent.

**Evidence:** `calls/CA46c26847a70632df26c4a1ec3bf96430_hours_inquiry_transcript.json`

---

## Bug 3: Transfer offer does not actually transfer

**Severity:** High
**Scenario:** `hours_inquiry`

When the caller asked to be connected to someone who could provide the exact
opening time (since the agent admitted it didn't know), the agent responded
*"Transferring you now. Thank you"* — but the call did not actually reach a
different person or department. It looped directly to the system's own
closing message ("You've reached the Pretty Good AI test line. Goodbye"),
ending the call rather than transferring it.

**Impact:** This is a broken escalation path. A caller who hits a dead end
and asks for a transfer — a completely reasonable next step — is told a
transfer is happening, but the call simply ends. This could feel like being
hung up on after being told help was coming.

---

## Bug 4: Inconsistent / apparently hallucinated hours information

**Severity:** High
**Scenario:** `edge_case_interruption`

The agent was asked for today's hours. It first responded: *"Usually clinics
are open until the late afternoon on **Saturdays in May**... but it can
vary."* The call took place on a **Friday**, not a Saturday, and the current
month was not May. Moments later in the same call, the agent gave a
different, apparently correct answer: *"Pivot Point Orthopedics is open
until noon today, **Friday**."*

**Impact:** The agent gave two different, mutually inconsistent answers to
the same question within a single conversation, one of which referenced a
day of the week and month that did not match the actual call. This looks
like a genuine hallucination rather than a data lookup returning a wrong but
consistent value, and is the most concerning finding in this test set —
inconsistent factual claims within a single conversation would seriously
undermine caller trust if this were a production system.

**Evidence:** `calls/CA9bd611c6ac9c31cacd860b221684099d_edge_case_interruption_transcript.json`

---

## Observation (not a bug): Agent interrupts caller mid-sentence

**Severity:** Low / informational

In one call, while the caller was still speaking ("Jordan Reyes. If you need
more to pull it up—"), the agent cut in with "Would you like to do that?"
before the caller had finished. This is the same category of turn-taking
imperfection our own bot had to explicitly fix during development — noted
here as a fair, comparable observation rather than a scored bug, since minor
turn-taking imperfections are common in current voice AI systems.

**Evidence:** `calls/CA9bd611c6ac9c31cacd860b221684099d_edge_case_interruption_transcript.json`

---

## Observation (not a bug): Auto-assigned demo profile data

**Severity:** Informational

When creating a "demo patient profile," the agent auto-assigned a fixed date
of birth ("July 4, 2000") without asking, regardless of what identity
information the caller actually provided. This is very likely intentional
placeholder behavior for a demo/test environment rather than a genuine bug,
but is noted here since it was a consistent, reproducible pattern across
multiple calls.

---

## Summary

| # | Bug | Severity | Scenario |
|---|-----|----------|----------|
| 1 | Vague deflection instead of direct answer | Medium | hours_inquiry |
| 2 | Explicit information gap on basic hours data | Medium | hours_inquiry |
| 3 | Transfer offer doesn't actually transfer | High | hours_inquiry |
| 4 | Inconsistent/hallucinated hours across same conversation | High | edge_case_interruption |

The two high-severity findings (broken transfer escalation, and internally
inconsistent hallucinated information) both relate to trust and reliability
failure modes that would matter most in a real deployment — a caller being
told help is coming when it isn't, and being given contradictory factual
claims within the same call.