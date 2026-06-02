"""
Package tools — ensemble d'outils pour l'assistant IA.

Chaque module enregistre ses fonctions via @register_tool.
L'import de ce package suffit à peupler TOOL_REGISTRY.
"""

from .registry import TOOL_REGISTRY, register_tool
from .decorators import safe_tool, cached

# --- Infrastructure partagée (depuis tools_legacy) ---
import tools_legacy as _legacy

set_voice_manager = _legacy.set_voice_manager
register_log_listener = _legacy.register_log_listener
log_action = _legacy.log_action
get_screen_resolution = _legacy.get_screen_resolution

# --- Importer tous les sous-modules pour déclencher l'enregistrement ---
from . import system
from . import input_tools
from . import files
from . import network
from . import web
from . import productivity
from . import media

# --- Ré-exporter TOUTES les fonctions de tools_legacy pour rétrocompatibilité ---
# Les modules comme agent.py, app.py, voice.py font "import tools" ou "from tools import ..."
import sys as _sys
_this_module = _sys.modules[__name__]

for _name in dir(_legacy):
    if not _name.startswith('_'):
        try:
            setattr(_this_module, _name, getattr(_legacy, _name))
        except AttributeError:
            pass