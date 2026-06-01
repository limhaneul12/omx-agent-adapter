import tomllib
from pathlib import Path

from omx_remote.shared.exceptions import TomlDocumentLoadError


def load_toml_document_object(
    config_path: Path, document_label: str
) -> dict[str, object]:
    """Load one TOML document into a root object.

    Args:
        config_path [Path]: TOML path to read.
        document_label [str]: Human-readable document label for errors.

    Returns:
        dict[str, object]: Parsed TOML root object.
    """
    try:
        config_text: str = config_path.read_text(encoding="utf-8")
        parsed_toml: dict[str, object] = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as error:
        raise TomlDocumentLoadError(
            f"{document_label} at {config_path} contains malformed TOML: {error}"
        ) from error
    except OSError as error:
        raise TomlDocumentLoadError(
            f"{document_label} at {config_path} could not be read: {error}"
        ) from error

    return parsed_toml
