"""Typed report projections; presentation cannot change findings or scores."""
import json
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class ReportBinding(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    source: Literal['document', 'context', 'customer', 'literal']
    path: str | None = Field(default=None, max_length=500)
    default: str | None = Field(default=None, max_length=500)
    fallback_customer: bool = False

    @model_validator(mode='after')
    def required_path(self):
        if (self.source in {'document', 'context'}) != bool(self.path):
            raise ValueError('Document/context bindings require a path; other sources cannot use one.')
        if self.source == 'document' and '.' not in self.path:
            raise ValueError('Document report bindings require profile.field paths.')
        if self.fallback_customer and self.source != 'document':
            raise ValueError('Customer fallback is supported only for document bindings.')
        return self


class ReportDefinition(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    timezone: str = Field(max_length=100)
    bindings: dict[str, ReportBinding]

    @field_validator('timezone')
    @classmethod
    def timezone_exists(cls, value):
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError('Choose a registered IANA timezone.') from exc
        return value


def defaults():
    return json.loads((Path(__file__).parents[1] / 'config_data/report_bindings_v1.json').read_text(encoding='utf-8'))


def definitions(configuration):
    return {key: ReportDefinition.model_validate(value) for key, value in
            {**defaults(), **configuration.get('report_definitions', {})}.items()}


def validate_report_definitions(configuration):
    raw = configuration.get('report_definitions', {})
    baseline = defaults()
    if not isinstance(raw, dict) or set(raw) - set(baseline):
        raise ValueError('Report definitions must use registered layout IDs.')
    from .identity import _resolve
    from .contexts import definitions as context_definitions
    contexts = context_definitions(configuration)
    for layout, value in raw.items():
        definition = ReportDefinition.model_validate(value)
        if set(definition.bindings) != set(baseline[layout]['bindings']):
            raise ValueError('Configure every supported report binding exactly once.')
        for binding in definition.bindings.values():
            if binding.source == 'document':
                profile, path = binding.path.split('.', 1)
                if profile not in configuration['profiles']:
                    raise ValueError('Report binding references an unknown document profile.')
                root = configuration['profiles'][profile]['schema']
                node = root
                for part in path.split('.'):
                    node = _resolve(node, root).get('properties', {}).get(part)
                    if not isinstance(node, dict):
                        raise ValueError('Report binding references an unknown schema field.')
            elif binding.source == 'context' and binding.path not in contexts:
                raise ValueError('Report bindings must use registered case context fields.')


def project_report(snapshot, layout):
    from app.sop import value_at
    definition = definitions(snapshot.get('configuration', {}))[layout]
    values = {}
    for key, binding in definition.bindings.items():
        if binding.source == 'document':
            value, matches = value_at(snapshot['documents'], binding.path)
            value = value if len(matches) == 1 else None
        elif binding.source == 'context':
            value = snapshot.get('case_context', {}).get(binding.path)
        elif binding.source == 'customer':
            value = snapshot['customer']
        else:
            value = binding.default
        if value in (None, ''):
            value = snapshot['customer'] if binding.fallback_customer else binding.default
        values[key] = value
    return values, definition.timezone
