# Contributor Guide

Welcome to the NOVA development ecosystem. As a developer, your primary task is to preserve core architectural invariants while shipping robust tools.

## General Principles

1. **Safety First**: Check whitelists in `validator.py` and authorization risk policies in `controller.py` before exposing new OS-level tools.
2. **Deterministic Memory**: Ensure any custom memory parser does not overwrite historical records.
3. **Tests Required**: Every new route or controller method must be verified by automated unit tests under the `tests/` directory.

## Code and Spec Sync

1. If you are modifying *what* the system does conceptually, write an **RFC** first.
2. If you are changing *how* a class or library is implemented, document it with an **ADR** (e.g., swapping a cryptography tool or vector model).
3. Update the inline documentation links. Ensure files import correctly using standard Python structures.
