"""Núcleo do antdpy: árvore de componentes e serialização para o front (Antd)."""

from __future__ import annotations

import dataclasses
import datetime as _dt
import decimal
import enum
import math
from typing import Any, Callable, Iterable


class _Unset:
    """Sentinela: "prop não informada" (diferente de None, que vira null no front)."""

    _instance: "_Unset | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Any = _Unset()


def to_camel(name: str) -> str:
    """snake_case -> camelCase (só no nome da prop de topo; dicts aninhados não mudam)."""
    if name.startswith("aria_"):
        return name.replace("_", "-")
    parts = name.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def _flatten(items: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    for item in items:
        if item is None or item is False or item is True or item is UNSET:
            continue  # permite `cond and ui.Text(...)`
        if isinstance(item, (list, tuple)) or (
            hasattr(item, "__iter__")
            and not isinstance(item, (str, bytes, dict, Component))
        ):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out


class Component:
    """Nó da árvore de UI. `TYPE` é o caminho do componente no Antd (ex.: "Form.Item")."""

    TYPE: str = ""

    def __init__(self, *children: Any, key: Any = None, **props: Any) -> None:
        self.type: str = self.TYPE
        self.key = key
        self.children: list[Any] = _flatten(children)
        self.props: dict[str, Any] = {
            k: v for k, v in props.items() if v is not UNSET
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.type} props={list(self.props)} children={len(self.children)}>"


def json_default(obj: Any) -> Any:
    if isinstance(obj, (_dt.datetime, _dt.date, _dt.time)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if hasattr(obj, "model_dump"):  # pydantic v2
        return obj.model_dump()
    if hasattr(obj, "item") and callable(obj.item):  # numpy escalar
        return obj.item()
    raise TypeError(f"Valor não serializável para o front: {type(obj).__name__}")


class Serializer:
    """Converte Components em JSON e registra callbacks (`on_*`) por id posicional."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[..., Any]] = {}

    def walk(self, value: Any, path: str) -> Any:
        if isinstance(value, Component):
            return self._node(value, path)
        if callable(value):
            self.handlers[path] = value
            return {"$event": path}
        if isinstance(value, dict):
            return {str(k): self.walk(v, f"{path}.{k}") for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.walk(v, f"{path}.{i}") for i, v in enumerate(value)]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    def _node(self, comp: Component, path: str) -> dict[str, Any]:
        props = {
            to_camel(k): self.walk(v, f"{path}.{k}") for k, v in comp.props.items()
        }
        children = [self.walk(c, f"{path}.c{i}") for i, c in enumerate(comp.children)]
        node: dict[str, Any] = {"$node": comp.type, "props": props, "children": children}
        if comp.key is not None:
            node["key"] = str(comp.key)
        return node


def serialize(tree: Component) -> tuple[dict[str, Any], dict[str, Callable[..., Any]]]:
    s = Serializer()
    return s.walk(tree, "r"), s.handlers
