"""Tests del parser de intenciones (ES/EN, wake word opcional, entidades)."""

from jarvis.core.intent_parser import IntentParser


def make_parser() -> IntentParser:
    return IntentParser()


class TestOpenCloseApps:
    def test_open_app_english(self):
        intent = make_parser().parse("open firefox")
        assert intent.name == "OPEN_APP"
        assert intent.entities["app"] == "firefox"

    def test_open_app_spanish(self):
        intent = make_parser().parse("abre spotify")
        assert intent.name == "OPEN_APP"
        assert intent.entities["app"] == "spotify"

    def test_open_app_with_wake_word(self):
        intent = make_parser().parse("jarvis open visual studio code")
        assert intent.name == "OPEN_APP"
        assert intent.entities["app"] == "visual studio code"

    def test_close_app(self):
        intent = make_parser().parse("cierra firefox")
        assert intent.name == "CLOSE_APP"
        assert intent.entities["app"] == "firefox"

    def test_case_and_whitespace_normalized(self):
        intent = make_parser().parse("   OPEN   Firefox   ")
        assert intent.name == "OPEN_APP"
        assert intent.entities["app"] == "firefox"


class TestMediaIntents:
    def test_play_music_english(self):
        assert make_parser().parse("play music").name == "MEDIA_PLAY"

    def test_play_music_spanish(self):
        assert make_parser().parse("pon musica").name == "MEDIA_PLAY"

    def test_pause_music(self):
        assert make_parser().parse("pause music").name == "MEDIA_PAUSE"

    def test_stop_music(self):
        assert make_parser().parse("deten musica").name == "MEDIA_STOP"


class TestFileIntents:
    def test_read_file_extracts_path(self):
        intent = make_parser().parse("read file /home/user/notes.md")
        assert intent.name == "FILE_READ"
        assert intent.entities["path"] == "/home/user/notes.md"

    def test_create_file_spanish(self):
        intent = make_parser().parse("crea file /tmp/informe.txt")
        assert intent.name == "FILE_CREATE"
        assert intent.entities["path"] == "/tmp/informe.txt"

    def test_search_files_with_and_without_scope(self):
        scoped = make_parser().parse("find files *.pdf in ~/docs")
        assert scoped.name == "FILE_SEARCH"
        assert scoped.entities["pattern"] == "*.pdf"
        assert scoped.entities["path"] == "~/docs"

        bare = make_parser().parse("busca files *.txt")
        assert bare.name == "FILE_SEARCH"
        assert bare.entities["pattern"] == "*.txt"


class TestSystemAndAgent:
    def test_time(self):
        assert make_parser().parse("que hora es").name == "SYSTEM_TIME"
        assert make_parser().parse("what time is it").name == "SYSTEM_TIME"

    def test_capabilities(self):
        assert make_parser().parse("help").name == "SYSTEM_CAPABILITIES"

    def test_calendar(self):
        assert make_parser().parse("upcoming events").name == "CALENDAR_UPCOMING"

    def test_agent_request_catches_free_form(self):
        intent = make_parser().parse("jarvis summarize my week and email Ana")
        assert intent.name == "AGENT_REQUEST"
        assert "summarize" in intent.entities["query"]

    def test_unknown_fallback(self):
        intent = make_parser().parse("quantum banana sandwich")
        assert intent.name == "UNKNOWN"
        assert intent.entities == {}

    def test_empty_text_is_unknown(self):
        assert make_parser().parse("   ").name == "UNKNOWN"


class TestCustomRules:
    def test_register_rule_with_extractor(self):
        parser = make_parser()
        parser.register_rule(
            r"^set volume (?P<level>\d+)$",
            "SET_VOLUME",
            extractor=lambda m: {"level": m.group("level")},
        )
        intent = parser.parse("set volume 40")
        assert intent.name == "SET_VOLUME"
        assert intent.entities["level"] == "40"

    def test_default_rules_keep_precedence_on_ambiguous_input(self):
        # "open everything" casa con OPEN_APP (defecto) antes que con reglas
        # nuevas: las reglas se evalúan en orden de registro y gana la primera.
        parser = make_parser()
        parser.register_rule(r"^open everything$", "OPEN_ALL")
        assert parser.parse("open everything").name == "OPEN_APP"
