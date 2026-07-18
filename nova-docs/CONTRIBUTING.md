# Contributing to NOVA Specifications

All contributions to the design or implementation of the NOVA system must follow a structured review process.

## The Proposal Workflow

1. **Research**: Consult prior research, ontology models, or open standards.
2. **Draft RFC**: Create a proposal in `RFC/Draft/` following [RFC/TEMPLATE.md](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/RFC/TEMPLATE.md).
3. **Review**: Submit a pull request to move the RFC to `RFC/Review/`. Focus on conceptual correctness and alignment with Core invariants.
4. **Acceptance**: Once approved, the RFC moves to `RFC/Accepted/`.
5. **Update NAS**: The author of the RFC updates the corresponding volume of the **NOVA Architecture Specification (NAS)** to reflect the changes.
6. **Implement**: Code development proceeds. Concrete implementation tradeoffs are recorded as **Architecture Decision Records (ADRs)** in `ADR/` following [ADR/TEMPLATE.md](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/ADR/TEMPLATE.md).
