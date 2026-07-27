from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple


@dataclass
class ValidationRule:
    field: str
    rule_type: str
    params: dict = field(default_factory=dict)
    severity: str = "error"
    message: str = ""


@dataclass
class ValidationResult:
    valid: bool = True
    errors: List[Tuple[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, field: str, message: str):
        self.valid = False
        self.errors.append((field, message))

    def add_warning(self, message: str):
        self.warnings.append(message)

    def merge(self, other: "ValidationResult"):
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


class DataValidator:
    REQUIRED = "required"
    NOT_EMPTY = "not_empty"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    REGEX = "regex"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    IS_NUMERIC = "is_numeric"
    IS_DATE = "is_date"
    IS_EMAIL = "is_email"
    IN_LIST = "in_list"
    MATCHES_PATTERN = "matches_pattern"

    VALIDATORS: Dict[str, Callable] = {}

    def __init__(self):
        self.rules: List[ValidationRule] = []

    def add_rule(self, rule: ValidationRule):
        self.rules.append(rule)

    def add_rules(self, rules: List[ValidationRule]):
        self.rules.extend(rules)

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        for rule in self.rules:
            value = data.get(rule.field)
            validator_fn = self.VALIDATORS.get(rule.rule_type)
            if not validator_fn:
                continue
            try:
                is_valid, message = validator_fn(value, rule)
                if not is_valid:
                    if rule.severity == "error":
                        result.add_error(rule.field, message)
                    else:
                        result.add_warning(message)
            except Exception as e:
                result.add_error(rule.field, f"Validation error: {e}")
        return result

    def build_from_config(self, rules_config: Dict[str, Any]):
        for field_name, field_rules in rules_config.items():
            if isinstance(field_rules, list):
                for rule_def in field_rules:
                    if isinstance(rule_def, str):
                        rule_type = rule_def
                        params = {}
                    else:
                        rule_type = rule_def.get("type", "required")
                        params = {k: v for k, v in rule_def.items() if k != "type"}
                    self.rules.append(ValidationRule(
                        field=field_name,
                        rule_type=rule_type,
                        params=params,
                        severity=rule_def.get("severity", "error") if isinstance(rule_def, dict) else "error",
                        message=rule_def.get("message", "") if isinstance(rule_def, dict) else "",
                    ))

    @classmethod
    def _check_required(cls, value: Any, rule: ValidationRule) -> Tuple[bool, str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, rule.message or f"{rule.field} is required"
        return True, ""

    @classmethod
    def _check_not_empty(cls, value: Any, rule: ValidationRule) -> Tuple[bool, str]:
        if isinstance(value, str) and not value.strip():
            return False, rule.message or f"{rule.field} must not be empty"
        if value is None:
            return False, rule.message or f"{rule.field} must not be empty"
        return True, ""

    @classmethod
    def _check_min_length(cls, value: Any, rule: ValidationRule) -> Tuple[bool, str]:
        min_len = rule.params.get("min", 1)
        if isinstance(value, str) and len(value.strip()) < min_len:
            return False, rule.message or f"{rule.field} must be at least {min_len} characters"
        return True, ""

    @classmethod
    def _check_regex(cls, value: Any, rule: ValidationRule) -> Tuple[bool, str]:
        pattern = rule.params.get("pattern", "")
        if isinstance(value, str) and not re.match(pattern, value):
            return False, rule.message or f"{rule.field} does not match required pattern"
        return True, ""

    @classmethod
    def _check_min_value(cls, value: Any, rule: ValidationRule) -> Tuple[bool, str]:
        min_val = rule.params.get("min", 0)
        try:
            if float(value) < min_val:
                return False, rule.message or f"{rule.field} must be >= {min_val}"
        except (ValueError, TypeError):
            return False, f"{rule.field} is not numeric"
        return True, ""


DataValidator.VALIDATORS = {
    DataValidator.REQUIRED: DataValidator._check_required,
    DataValidator.NOT_EMPTY: DataValidator._check_not_empty,
    DataValidator.MIN_LENGTH: DataValidator._check_min_length,
    DataValidator.REGEX: DataValidator._check_regex,
    DataValidator.MIN_VALUE: DataValidator._check_min_value,
}
