"""
Outils productivité : calendrier, minuteur, notes, calculs, conversions.
"""
from .registry import register_tool
from .decorators import safe_tool
import tools_legacy as _legacy


@register_tool(
    name="add_calendar_event",
    description="Ajoute un événement dans le calendrier Outlook/Windows.",
    category="Productivité",
    aliases=["calendar", "event", "calendrier", "ajouter_evenement", "schedule"],
    parameters={
        "title": {
            "type": "string",
            "description": "Titre de l'événement.",
            "required": True,
        },
        "start_time": {
            "type": "string",
            "description": "Date/heure de début (YYYY-MM-DD HH:MM).",
            "required": True,
        },
        "end_time": {
            "type": "string",
            "description": "Date/heure de fin (YYYY-MM-DD HH:MM).",
            "required": False,
        },
        "location": {
            "type": "string",
            "description": "Lieu de l'événement.",
            "required": False,
        },
        "description": {
            "type": "string",
            "description": "Description de l'événement.",
            "required": False,
        },
    },
)
def add_calendar_event(title: str, start_time: str, end_time: str = "", location: str = "", description: str = ""):
    return _legacy.add_calendar_event(title, start_time, end_time, location, description)


@register_tool(
    name="set_timer",
    description="Définit un minuteur/compte à rebours.",
    category="Productivité",
    aliases=["timer", "minuteur", "countdown", "reminder", "rappel"],
    parameters={
        "seconds": {
            "type": "integer",
            "description": "Durée en secondes.",
            "required": True,
        },
        "message": {
            "type": "string",
            "description": "Message à afficher à la fin.",
            "required": False,
        },
    },
)
def set_timer(seconds: int, message: str = "Temps écoulé !"):
    return _legacy.set_timer(seconds, message)


@register_tool(
    name="take_note",
    description="Prend une note rapide et l'enregistre.",
    category="Productivité",
    aliases=["note", "memo", "prendre_note", "quick_note", "notepad"],
    parameters={
        "text": {
            "type": "string",
            "description": "Contenu de la note.",
            "required": True,
        },
        "title": {
            "type": "string",
            "description": "Titre de la note (optionnel).",
            "required": False,
        },
    },
)
def take_note(text: str, title: str = ""):
    return _legacy.take_note(text, title)


@register_tool(
    name="calculate",
    description="Évalue une expression mathématique.",
    category="Productivité",
    aliases=["calc", "calculer", "math", "eval", "expression", "compute"],
    parameters={
        "expression": {
            "type": "string",
            "description": "Expression mathématique (ex: 2+2, sqrt(16), sin(pi/2)).",
            "required": True,
        },
    },
)
def calculate(expression: str):
    return _legacy.calculate(expression)


@register_tool(
    name="convert_units",
    description="Convertit des unités (longueur, masse, température, etc.).",
    category="Productivité",
    aliases=["convert", "convertir", "unites", "conversion", "unit_converter"],
    parameters={
        "value": {
            "type": "number",
            "description": "Valeur à convertir.",
            "required": True,
        },
        "from_unit": {
            "type": "string",
            "description": "Unité source (ex: km, m, cm, kg, g, celsius, fahrenheit...).",
            "required": True,
        },
        "to_unit": {
            "type": "string",
            "description": "Unité cible.",
            "required": True,
        },
    },
)
def convert_units(value: float, from_unit: str, to_unit: str):
    return _legacy.convert_units(value, from_unit, to_unit)


@register_tool(
    name="get_current_datetime",
    description="Récupère la date et l'heure actuelles.",
    category="Productivité",
    aliases=["datetime", "time", "date", "horloge", "maintenant", "now"],
)
def get_current_datetime():
    return _legacy.get_current_datetime()


@register_tool(
    name="set_alarm",
    description="Définit une alarme pour une heure donnée.",
    category="Productivité",
    aliases=["alarm", "alarme", "wake_up", "reveil"],
    parameters={
        "time": {
            "type": "string",
            "description": "Heure de l'alarme (HH:MM).",
            "required": True,
        },
        "message": {
            "type": "string",
            "description": "Message de l'alarme.",
            "required": False,
        },
    },
)
def set_alarm(time: str, message: str = "Alarme !"):
    return _legacy.set_alarm(time, message)