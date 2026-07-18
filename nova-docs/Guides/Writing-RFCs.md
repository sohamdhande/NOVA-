# Writing Request for Comments (RFCs)

This guide outlines the rules for proposing modifications or additions to the NOVA Architecture Specification.

## The Proposal Life Cycle

Every proposed change to the NAS follows a strict progression:

```
[Draft] ────► [Review] ────► [Accepted] ────► [Merged into NAS]
  │                             │
  └─────────────────────────────┼───────────► [Rejected]
                                │
                                └───────────► [Superseded] (Later)
```

1. **Draft State**: Copy [RFC/TEMPLATE.md](file:///Users/sohamdhande/Docs_Local/NOVA/nova-docs/RFC/TEMPLATE.md) into `RFC/Draft/` naming it `RFC-XXXX-your-topic-name.md`. Substitute `XXXX` with the next sequential RFC number. Fill out the sections thoroughly.
2. **Review State**: Open a Pull Request to move the file to `RFC/Review/`. Inform the core team to initiate discussion.
3. **Accepted State**: Once consensus is achieved, the PR is merged, and the file moves to `RFC/Accepted/`.
4. **Integration**: The author updates the target `NAS/` volume files with the newly accepted rules, linking to the accepted RFC. The RFC remains in the `Accepted/` directory as historical evidence.
