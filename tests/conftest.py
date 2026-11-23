"""Configuración común de tests: hace importable el paquete `jarvis`.

Funciona tanto con `pytest` (el path de pytest sólo incluye `tests/`) como
con `python -m pytest` (cwd va en el path).
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
