"""
Outils système : résolution, luminosité, volume, processus, alimentation.
"""
from .registry import register_tool
from .decorators import safe_tool
import tools_legacy as _legacy


@register_tool(
    name="get_screen_resolution",
    description="Obtenir la résolution de l'écran (largeur, hauteur).",
    category="Système",
    aliases=["screen_resolution", "resolution"],
)
def get_screen_resolution():
    return _legacy.get_screen_resolution()


@register_tool(
    name="get_active_window_title",
    description="Récupère le titre de la fenêtre active.",
    category="Système",
    aliases=["active_window", "window_title", "fenetre_active"],
)
def get_active_window_title():
    return _legacy.get_active_window_title()


@register_tool(
    name="get_running_processes",
    description="Liste les processus en cours d'exécution.",
    category="Système",
    aliases=["processes", "tasklist", "processus"],
)
def get_running_processes():
    return _legacy.get_running_processes()


@register_tool(
    name="get_battery_status",
    description="Récupère l'état de la batterie (pourcentage, branché ou non).",
    category="Système",
    aliases=["battery", "batterie", "power_status"],
)
def get_battery_status():
    return _legacy.get_battery_status()


@register_tool(
    name="set_brightness",
    description="Change la luminosité de l'écran (0-100).",
    category="Système",
    aliases=["brightness", "luminosite", "screen_brightness"],
    parameters={
        "level": {
            "type": "integer",
            "description": "Niveau de luminosité (0 à 100).",
            "required": True,
        }
    },
)
def set_brightness(level: int):
    return _legacy.set_brightness(level)


@register_tool(
    name="set_volume",
    description="Change le volume système (0-100).",
    category="Système",
    aliases=["volume", "sound", "audio_volume"],
    parameters={
        "level": {
            "type": "integer",
            "description": "Niveau de volume (0 à 100).",
            "required": True,
        }
    },
)
def set_volume(level: int):
    return _legacy.set_volume(level)


@register_tool(
    name="lock_screen",
    description="Verrouille la session Windows.",
    category="Système",
    aliases=["lock", "verrouiller", "lock_session"],
)
def lock_screen():
    return _legacy.lock_screen()


@register_tool(
    name="get_clipboard_text",
    description="Récupère le texte actuellement dans le presse-papiers.",
    category="Système",
    aliases=["clipboard", "presse_papiers", "get_clipboard"],
)
def get_clipboard_text():
    return _legacy.get_clipboard_text()