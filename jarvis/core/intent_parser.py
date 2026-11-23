from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from re import Pattern


@dataclass()
class Intent:
    name: str
    entities: dict[str, str] = field(default_factory=dict)
    text: str = ""


@dataclass()
class IntentRule:
    pattern: Pattern[str]
    intent_name: str
    extractor: Callable[[re.Match[str]], dict[str, str]] | None = None


class IntentParser:
    def __init__(self) -> None:
        self._rules: list[IntentRule] = []
        self._register_default_rules()

    def register_rule(
        self,
        regex: str,
        intent_name: str,
        extractor: Callable[[re.Match[str]], dict[str, str]] | None = None,
    ) -> None:
        compiled = re.compile(regex, flags=re.IGNORECASE)
        self._rules.append(
            IntentRule(pattern=compiled, intent_name=intent_name, extractor=extractor)
        )

    def parse(self, text: str) -> Intent:
        normalized = text.strip().lower()
        for rule in self._rules:
            match = rule.pattern.search(normalized)
            if not match:
                continue
            entities = rule.extractor(match) if rule.extractor else match.groupdict()
            return Intent(name=rule.intent_name, entities=entities, text=normalized)
        return Intent(name="UNKNOWN", entities={}, text=normalized)

    def _register_default_rules(self) -> None:
        wake_prefix = r"(?:(?:jarvis|yarvis)\s+)?"
        self.register_rule(
            rf"^{wake_prefix}(?:open|launch|start|abre|abrir|inicia|iniciar|lanza|lanzar)"
            rf"\s+(?P<app>[a-z0-9_\-\. ]+)$",
            "OPEN_APP",
            extractor=lambda m: {"app": m.group("app").strip()},
        )
        self.register_rule(rf"^{wake_prefix}(?:show|list|muestra|listar)\s+apps$", "LIST_APPS")
        self.register_rule(
            rf"^{wake_prefix}(?:close|quit|exit|kill|cerrar|cierra)\s+(?P<app>[a-z0-9_\-\. ]+)$",
            "CLOSE_APP",
            extractor=lambda m: {"app": m.group("app").strip()},
        )
        self.register_rule(
            rf"^{wake_prefix}(?:play|start|pon|reproduce)\s+music(?:a)?$", "MEDIA_PLAY"
        )
        self.register_rule(
            rf"^{wake_prefix}(?:pause|resume|pausa|reanuda)\s+music(?:a)?$",
            "MEDIA_PAUSE",
        )
        self.register_rule(rf"^{wake_prefix}(?:stop|deten|parar)\s+music(?:a)?$", "MEDIA_STOP")
        self.register_rule(
            rf"^{wake_prefix}(?:read|open|lee|abre)\s+file\s+(?P<path>.+)$", "FILE_READ"
        )
        self.register_rule(
            rf"^{wake_prefix}(?:create|write|new|crear|crea)\s+file\s+(?P<path>.+)$",
            "FILE_CREATE",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:delete|remove|erase|elimina|borra)\s+file\s+(?P<path>.+)$",
            "FILE_DELETE",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:analyze|summarize|investigate|analiza|resume|investiga)\s+file\s+(?P<path>.+)$",
            "FILE_SUMMARY",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:list|show|listar|muestra)\s+files(?:\s+in)?\s+(?P<path>.+)$",
            "FILE_LIST",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:find|search|busca)\s+files\s+(?P<pattern>[^\s]+)(?:\s+in\s+(?P<path>.+))?$",
            "FILE_SEARCH",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:what(?:'s| is)\s+on\s+my\s+calendar|upcoming\s+events|"
            rf"que\s+tengo\s+en\s+el\s+calendario)$",
            "CALENDAR_UPCOMING",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:find|search|busca)\s+contact\s+(?P<query>.+)$",
            "CONTACT_SEARCH",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:do|execute|run|ejecuta)\s+task\s+(?P<goal>.+)$",
            "TASK_SUBMIT",
        )
        self.register_rule(rf"^{wake_prefix}(?:list|show|listar|muestra)\s+tasks$", "TASK_LIST")
        self.register_rule(
            rf"^{wake_prefix}(?:what\s+time\s+is\s+it|time|que\s+hora\s+es)$",
            "SYSTEM_TIME",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:shutdown\s+system|power\s+off|apaga\s+el\s+sistema)$",
            "SHUTDOWN_SYSTEM",
        )
        self.register_rule(
            rf"^{wake_prefix}(?:what\s+can\s+you\s+do|help|ayuda|que\s+puedes\s+hacer)$",
            "SYSTEM_CAPABILITIES",
        )
        self.register_rule(r"^(?:jarvis|yarvis|assistant)\s+(?P<query>.+)$", "AGENT_REQUEST")
