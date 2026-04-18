from __future__ import annotations

import importlib
import logging
import pkgutil
from types import ModuleType
from typing import Any
from typing import Callable

from jarvis.core.command_registry import CommandRegistry
from jarvis.core.intent_parser import IntentParser


LOGGER = logging.getLogger(__name__)


class PluginContext:
    def __init__(self, parser: IntentParser, commands: CommandRegistry) -> None:
        self.parser = parser
        self.commands = commands


PluginRegisterV1 = Callable[[IntentParser], None]
PluginRegisterV2 = Callable[[PluginContext], None]


class PluginManager:
    def __init__(self, package_name: str = "jarvis.plugins") -> None:
        self._package_name = package_name
        self._loaded_modules: list[str] = []

    @property
    def loaded_modules(self) -> list[str]:
        return list(self._loaded_modules)

    def load(self, parser: IntentParser, commands: CommandRegistry) -> None:
        package = importlib.import_module(self._package_name)
        for module_info in pkgutil.iter_modules(package.__path__, prefix=f"{self._package_name}."):
            module_name = module_info.name
            module = importlib.import_module(module_name)
            if self._register_module(module, parser, commands):
                self._loaded_modules.append(module_name)
                LOGGER.info("Loaded plugin module %s", module_name)

    def _register_module(self, module: ModuleType, parser: IntentParser, commands: CommandRegistry) -> bool:
        register = getattr(module, "register", None)
        if not callable(register):
            return False

        context = PluginContext(parser=parser, commands=commands)

        try:
            register(context)
        except TypeError:
            register(parser)

        return True
