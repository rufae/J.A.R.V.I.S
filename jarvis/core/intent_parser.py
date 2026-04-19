from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Pattern


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
        self._rules.append(IntentRule(pattern=compiled, intent_name=intent_name, extractor=extractor))

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
        self.register_rule(
            r"^(?:open|launch|start)\s+(?P<app>[a-z0-9_-]+)$",
            "OPEN_APP",
        )
        self.register_rule(r"^(?:show|list)\s+apps$", "LIST_APPS")
        self.register_rule(r"^(?:play|start)\s+music$", "MEDIA_PLAY")
        self.register_rule(r"^(?:pause|resume)\s+music$", "MEDIA_PAUSE")
        self.register_rule(r"^(?:stop)\s+music$", "MEDIA_STOP")
        self.register_rule(r"^(?:read|open)\s+file\s+(?P<path>.+)$", "FILE_READ")
        self.register_rule(r"^(?:list|show)\s+files(?:\s+in)?\s+(?P<path>.+)$", "FILE_LIST")
        self.register_rule(
            r"^(?:find|search)\s+files\s+(?P<pattern>[^\s]+)(?:\s+in\s+(?P<path>.+))?$",
            "FILE_SEARCH",
        )
        self.register_rule(r"^(?:what(?:'s| is)\s+on\s+my\s+calendar|upcoming\s+events)$", "CALENDAR_UPCOMING")
        self.register_rule(r"^(?:find|search)\s+contact\s+(?P<query>.+)$", "CONTACT_SEARCH")
        self.register_rule(r"^(?:do|execute|run)\s+task\s+(?P<goal>.+)$", "TASK_SUBMIT")
        self.register_rule(r"^(?:list|show)\s+tasks$", "TASK_LIST")
        self.register_rule(r"^(?:what\s+time\s+is\s+it|time)$", "SYSTEM_TIME")
        self.register_rule(r"^(?:shutdown\s+system|power\s+off)$", "SHUTDOWN_SYSTEM")
        self.register_rule(r"^(?:what\s+can\s+you\s+do|help)$", "SYSTEM_CAPABILITIES")
        self.register_rule(r"^(?:jarvis|assistant)\s+(?P<query>.+)$", "AGENT_REQUEST")
