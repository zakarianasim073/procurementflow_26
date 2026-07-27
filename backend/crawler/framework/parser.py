from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .logger import get_logger

log = get_logger("crawler.parser")

T = TypeVar("T", bound=BaseModel)


@dataclass
class ParseResult(Generic[T]):
    success: bool
    data: Optional[T] = None
    raw: Optional[Dict[str, Any]] = None
    normalized: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class Normalizer:
    TRANSFORMATIONS: Dict[str, Callable] = {
        "strip": lambda v: v.strip() if isinstance(v, str) else v,
        "lower": lambda v: v.lower() if isinstance(v, str) else v,
        "upper": lambda v: v.upper() if isinstance(v, str) else v,
        "remove_extra_spaces": lambda v: re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v,
        "remove_commas": lambda v: v.replace(",", "") if isinstance(v, str) else v,
        "to_int": lambda v: int(v.replace(",", "")) if isinstance(v, str) and v.strip() else v,
        "to_float": lambda v: float(v.replace(",", "")) if isinstance(v, str) and v.strip() else v if isinstance(v, (int, float)) else v,
        "to_bool": lambda v: v.lower() in ("yes", "true", "1", "y") if isinstance(v, str) else bool(v),
        "empty_to_none": lambda v: None if isinstance(v, str) and not v.strip() else v,
    }

    @staticmethod
    def apply(value: Any, chain: List[str]) -> Any:
        result = value
        for transform in chain:
            if transform in Normalizer.TRANSFORMATIONS:
                try:
                    result = Normalizer.TRANSFORMATIONS[transform](result)
                except (ValueError, TypeError, AttributeError) as e:
                    log.warning("normalize_failed", transform=transform, value=value, error=e)
        return result

    @staticmethod
    def bdt_to_number(value: str) -> Optional[float]:
        if not value:
            return None
        cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def parse_date(value: str, formats: Optional[List[str]] = None) -> Optional[str]:
        if not value:
            return None
        formats = formats or [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%Y/%m/%d",
            "%d %b %Y", "%d %B %Y",
            "%b %d, %Y", "%B %d, %Y",
            "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S",
            "%d-%b-%Y", "%Y%m%d",
        ]
        value = value.strip()
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).isoformat()
            except (ValueError, TypeError):
                continue
        return value


class FieldMapping:
    def __init__(
        self,
        source_keys: List[str],
        target_field: str,
        normalize: Optional[List[str]] = None,
        required: bool = False,
        default: Any = None,
    ):
        self.source_keys = source_keys
        self.target_field = target_field
        self.normalize = normalize or ["strip", "empty_to_none"]
        self.required = required
        self.default = default

    def extract(self, source: Dict[str, Any]) -> Any:
        for key in self.source_keys:
            for source_key in source:
                if source_key.lower().strip().startswith(key.lower().strip()):
                    value = source[source_key]
                    if self.normalize:
                        return Normalizer.apply(value, self.normalize)
                    return value
        if self.required:
            raise ValueError(f"Required field '{self.target_field}' not found (sources: {self.source_keys})")
        return self.default


class SchemaMapper:
    def __init__(self, mappings: List[FieldMapping]):
        self.mappings = mappings

    def map(self, source: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        errors = []
        for mapping in self.mappings:
            try:
                result[mapping.target_field] = mapping.extract(source)
            except ValueError as e:
                errors.append(str(e))
        return result, errors

    @classmethod
    def from_dict(cls, mapping_config: Dict[str, Any]) -> "SchemaMapper":
        mappings = []
        for target, config in mapping_config.items():
            if isinstance(config, dict):
                source_keys = config.get("sources", [target])
                normalize = config.get("normalize")
                required = config.get("required", False)
                default = config.get("default", None)
            else:
                source_keys = [config] if isinstance(config, str) else config
                normalize = None
                required = False
                default = None
            mappings.append(FieldMapping(
                source_keys=source_keys if isinstance(source_keys, list) else [source_keys],
                target_field=target,
                normalize=normalize,
                required=required,
                default=default,
            ))
        return cls(mappings)


class UniversalParser:
    def __init__(
        self,
        model_class: Optional[Type[T]] = None,
        mapper: Optional[SchemaMapper] = None,
    ):
        self.model_class = model_class
        self.mapper = mapper

    def parse_dict(self, raw: Dict[str, Any]) -> ParseResult:
        result = ParseResult(raw=raw)

        if self.mapper:
            try:
                normalized, errors = self.mapper.map(raw)
                result.normalized = normalized
                result.errors.extend(errors)
            except Exception as e:
                result.success = False
                result.errors.append(str(e))
                return result
        else:
            result.normalized = raw

        if self.model_class:
            try:
                instance = self.model_class(**result.normalized)
                result.data = instance
                result.success = True
            except ValidationError as e:
                result.success = False
                for err in e.errors():
                    result.errors.append(f"{'.'.join(err['loc'])}: {err['msg']}")
        else:
            result.success = True

        return result

    def parse_json(self, json_str: str) -> ParseResult:
        try:
            raw = json.loads(json_str)
        except json.JSONDecodeError as e:
            return ParseResult(success=False, errors=[f"Invalid JSON: {e}"])
        return self.parse_dict(raw)

    @classmethod
    def from_model(cls, model_class: Type[T], field_mapping: Optional[Dict] = None) -> "UniversalParser":
        mapper = SchemaMapper.from_dict(field_mapping) if field_mapping else None
        return cls(model_class=model_class, mapper=mapper)
