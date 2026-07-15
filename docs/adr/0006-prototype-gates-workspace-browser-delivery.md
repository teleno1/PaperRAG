# Prototype gates workspace browser delivery

Status: Accepted

Date: 2026-07-15

## Context

The completed browser slices established functional workflow and provenance
behaviour, but their minimal interface was built under an earlier fixed
three-panel assumption. The Workspace Owner found that this hides necessary
controls and produces an uncomfortable interaction, while the newly specified
real evidence-driven report workflow adds further states that the old layout
never considered. Continuing with minimal UI in each remaining vertical slice
would make that assumption progressively more expensive to remove.

## Decision

Before any unfinished browser-bearing delivery ticket starts, PaperRAG will
create an isolated, high-fidelity desktop Interaction Prototype using
controlled fixture data and simulated providers. It will first compare at least
three operable, materially different architecture candidates--a flow-driven
workspace, report-driven writing desk, and evidence-driven research desk--over
the complete normal journey. The Workspace Owner may then select, combine, and
iterate on a direction until explicitly accepting one architecture.

The accepted direction must cover the full prototype journey, including normal,
failure, recovery, evidence-gap, multi-source, and citation-review states, and
must produce an Interaction Contract. That contract inventories the controls,
state transitions, recovery paths, confirmation rules, and domain-object
mapping that later browser acceptance must honour. The prototype runs separately
from production APIs and persistence, uses desktop browsers only, and never
substitutes for real-provider product acceptance. The old three-panel layout is
a historical candidate rather than a constraint. The journey includes a Paper
Reading View that renders the selected paper's authorised original PDF and
opens Claim Citations at their anchored page; it does not reconstruct a paper
from Chunks or expand into annotation or PDF-editing features.

Prototype acceptance has two gates: the Workspace Owner first completes the
normal journey in every candidate and selects, combines, or redirects a
direction; the resulting single architecture then covers the full journey and
its recovery states before the owner accepts its Interaction Contract. Only the
second gate unblocks browser-bearing delivery work.

## Consequences

The current delivery frontier moves from real report-outline implementation to
the prototype decision work, and the remaining vertical delivery tickets wait
for explicit prototype acceptance. This delays feature implementation but
avoids hardening an interaction architecture that is already known to be
unacceptable. Once accepted, the prototype code remains disposable; its
interaction decisions and contract, not its mocked data or implementation,
guide production integration.
