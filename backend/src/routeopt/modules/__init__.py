"""Feature modules of the modular monolith (docs/ARCHITECTURE.md ADR-004).

Each module owns its router + service and stays independently extractable into a
microservice later. Cross-module access goes through services, never direct model
imports across module boundaries.
"""
