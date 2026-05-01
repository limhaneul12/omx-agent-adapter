# Pydantic Overview

## Goal

Use one strong contract language across the repository so that OMX control surfaces stay explicit, typed, and predictable.

This repository is not a domain-heavy backend. It is a contract-heavy adapter layer around OMX. Because of that, schema design is a first-class concern and Pydantic v2 is the primary schema system.

## Core Direction

- Use **Pydantic v2** as the standard schema system.
- Treat schemas as contracts, not incidental helper objects.
- Prefer consistent schema modeling over mixing multiple competing model styles.
- Missing or unclear contracts should be fixed with better schemas, not hidden with permissive structures.

## Project Stance

### Default

Use Pydantic v2 for:
- request payloads
- response payloads
- runtime snapshots
- execution events
- team state payloads
- bridge/probe/envelope payloads
- normalized OMX output structures
- validated config/settings when schema validation is useful

### Dataclass stance

Do not maintain dataclasses as a parallel primary contract system.

This repository does not follow a backend-style split where one model system is used for boundaries and another for most internal contract objects by default.

If an object behaves like a contract, it should usually be a Pydantic model.

### Exception bar

A non-Pydantic approach should only be introduced when there is a concrete, documented reason that Pydantic is not serving that case well enough.

## Design Principle

Pydantic is not just for API edges in this repository.
It is the main contract language that makes OMX easier and safer for agents to use.
