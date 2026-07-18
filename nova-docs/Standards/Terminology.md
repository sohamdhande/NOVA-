# Terminology and Ontology Standards

This document establishes the canonical vocabulary for the NOVA Architecture Specification (NAS). All documentation and code naming conventions must align with these terms.

## Ontological Layers

### Layer 0 — Universal Primitives
* **Identity**: Unique, immutable identifier corresponding to an Entity or Event.
* **Artifact**: Raw, immutable data from organizational activity.
* **Event**: Timestamped record of action.
* **Entity**: Independent, nameable concept.
* **Relationship**: Typed link between Entities or Events.
* **Assertion**: Structured semantic claim.
* **Evidence**: Source records or validation traces supporting or opposing an assertion.
* **Provenance**: Lineage derivation trace.
* **State**: Inferred snapshot condition of system relationships.
* **Change**: Transition path from State $A \rightarrow B$ triggered by Events.

### Layer 1 — Knowledge Primitives
* **Observation**: Semantic signal grouping.
* **Interpretation**: Mapping observations to domain definitions.
* **Claim**: An assertion pending verification.
* **Hypothesis**: Testable claim.
* **Experiment**: Contextual verification attempt.
* **Outcome**: Evaluated result of an experiment or choice.
* **Decision**: Committed constraint choice.
* **Goal**: Target objective state.
* **Metric**: Quantifiable measurement.
* **Task**: Planned task unit.
* **Constraint**: Invariant rule bounding actions.
* **Capability**: Enduring abstract utility of a component.
* **Intent**: Desired change state.
* **Policy**: Execution rules.

### Layer 2 — Domain Primitives
* **Project**: Bounded scope of activities.
* **Team** / **Person**: Agents.
* **Feature**: Set of capabilities.
* **API**: Execution contract.
* **Bug**: Identified variation from design spec.
* **Repository**: Git storage.
* **Roadmap**: Linear milestones plan.
* **Meeting**: Event block.
* **Document**: Project output projection.
