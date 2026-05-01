# ConfigDict and Model Shape Rules

## ConfigDict Rule

Use `model_config = ConfigDict(...)` explicitly when a schema needs configuration.

Do not copy the same `ConfigDict` block into every schema by habit.

### Preferred direction

- Choose `ConfigDict` options intentionally.
- Add only the options that match the contract.
- Avoid template-style config copy-paste.

### Common options to consider intentionally

- `extra`
- `strict`
- `frozen`
- `populate_by_name`
- `from_attributes`

### Project stance

`ConfigDict` should be optimized for each schema’s actual job.
It is not a one-size-fits-all default block.

## BaseModel Rule

Use `BaseModel` for normal named-field contracts.

This is the default shape for most schemas in this repository.

Examples:
- runtime status
- execution event
- team status
- search request
- normalized payload response

## RootModel Rule

`RootModel` is allowed, but only when the payload truly is a root value contract.

Examples of acceptable `RootModel` usage:
- the entire payload is a list
- the entire payload is a dictionary
- the entire payload is a single root value with no meaningful named wrapper fields

### Project stance

- `RootModel` is not the default.
- Use `BaseModel` for ordinary named-field contracts.
- Use `RootModel` only when the payload shape clearly demands it.

If the answer to “is the root itself the contract?” is not clearly yes, use `BaseModel`.

## Model API Rule

Prefer Pydantic v2 APIs consistently.

Preferred methods:
- `model_validate(...)`
- `model_validate_json(...)`
- `model_dump(...)`
- `model_dump_json(...)`

Avoid carrying older v1-style parsing and dumping habits into this repository.
