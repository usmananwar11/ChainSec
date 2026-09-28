"""Minimal JSON Schema (draft 2020-12 subset) validator. Python 3 standard library only.

Supports: type, enum, required, properties, additionalProperties (bool or schema),
items, minItems, minLength, minimum, $ref ("#/$defs/<name>").
"""
import json

_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(instance, schema, root=None, path="$"):
    root = schema if root is None else root
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ValueError(f"unsupported $ref {ref}")
        return validate(instance, root["$defs"][ref[len("#/$defs/"):]], root, path)
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](instance) for x in types):
            return [f"{path}: expected {'|'.join(types)}, got {type(instance).__name__}"]
    errors = []
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str) and len(instance) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than {schema['minLength']}")
    if _TYPES["number"](instance) and "minimum" in schema and instance < schema["minimum"]:
        errors.append(f"{path}: below minimum {schema['minimum']}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += validate(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], root, f"{path}.{key}")
            elif extra is False:
                errors.append(f"{path}: unexpected property '{key}'")
            elif isinstance(extra, dict):
                errors += validate(value, extra, root, f"{path}.{key}")
    return errors
