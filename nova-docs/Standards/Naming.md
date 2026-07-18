# Naming Standards

This standard governs the naming conventions for all specifications, records, and directories within the NOVA documentation repository.

## File Names
* All documentation files must use **kebab-case** (e.g., `compiler-first.md`).
* Specification files must be prefixed with their zero-padded identifier:
  * **Architecture Specification**: `NAS-###-concept-name.md` (e.g., `NAS-001-Theory-of-Organizational-Knowledge.md`).
  * **Architecture Decision Records**: `ADR-####-title.md` (e.g., `ADR-0001-Compiler-First.md`).
  * **Request for Comments**: `RFC-####-title.md` (e.g., `RFC-0001-Graph-Storage.md`).

## Entity & Event Identifiers
* **Entities**: Must use UUIDv4 strings for global database identification, and `kebab-case` for human-readable labels (e.g., `stripe-integration`).
* **Events**: Named using Past Tense verbs (`[Noun][Verb-ed]`), e.g., `DecisionAccepted`, `FeatureMerged`.
* **Classes / Types**: Represented in `PascalCase`.
* **Variables / Fields**: Represented in `snake_case` in Python backends, and `camelCase` in TypeScript frontends.
