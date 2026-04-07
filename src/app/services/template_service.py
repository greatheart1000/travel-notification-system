from __future__ import annotations

from dataclasses import dataclass, field

from app.core.entities import EventName, Template


@dataclass(slots=True)
class TemplateService:
    templates: list[Template] = field(default_factory=list)

    def upsert_template(self, template: Template) -> None:
        self.templates = [
            t
            for t in self.templates
            if not (
                t.event_name == template.event_name
                and t.locale == template.locale
                and t.version == template.version
                and t.ab_bucket == template.ab_bucket
            )
        ] + [template]

    def pick_template(self, event_name: EventName, locale: str, ab_bucket: str = "A") -> Template:
        enabled = [
            t
            for t in self.templates
            if t.event_name == event_name and t.locale == locale and t.enabled and t.ab_bucket == ab_bucket
        ]
        if not enabled:
            enabled = [
                t for t in self.templates if t.event_name == event_name and t.locale == "zh" and t.enabled
            ]
        if not enabled:
            raise ValueError(f"template missing for {event_name}")
        return sorted(enabled, key=lambda x: x.version, reverse=True)[0]

    def render(self, template: Template, variables: dict[str, str]) -> str:
        content = template.content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        return content
