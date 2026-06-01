"""Small TOML rendering helpers for generated adapter configuration files."""

import orjson


def toml_string(value: str) -> str:
    """Render one Python string as a TOML-compatible basic string.

    Args:
        value [str]: String value.

    Returns:
        str: Quoted TOML string.
    """
    rendered_value: str = orjson.dumps(value).decode()
    return rendered_value


def toml_multiline_string(value: str) -> str:
    """Render one Python string as a TOML multiline basic string.

    Args:
        value [str]: String value.

    Returns:
        str: TOML multiline string literal.
    """
    escaped_value: str = value.replace('"""', '\\"\\"\\"')
    rendered_value: str = f'"""{escaped_value}"""'
    return rendered_value


def toml_array(values: tuple[str, ...]) -> str:
    """Render a TOML string array.

    Args:
        values [tuple[str, ...]]: String values.

    Returns:
        str: TOML array.
    """
    rendered_array: str = "[" + ", ".join(toml_string(value) for value in values) + "]"
    return rendered_array


def toml_inline_table(values: dict[str, str]) -> str:
    """Render a TOML inline table for string key/value pairs.

    Args:
        values [dict[str, str]]: Inline table values.

    Returns:
        str: TOML inline table.
    """
    entries = tuple(
        f"{toml_string(name)} = {toml_string(value)}"
        for name, value in sorted(values.items())
    )
    rendered_table: str = "{ " + ", ".join(entries) + " }"
    return rendered_table
