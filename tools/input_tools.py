"""
Outils de saisie/contrôle : souris, clavier, OCR, screenshot.
"""
from .registry import register_tool
from .decorators import safe_tool
import tools_legacy as _legacy


# --- Mouse Tools ---

@register_tool(
    name="move_mouse",
    description="Déplace la souris aux coordonnées (x, y).",
    category="Contrôle / Saisie",
    aliases=["mouse_move", "souris_deplace", "move_cursor"],
    parameters={
        "x": {"type": "integer", "description": "Coordonnée X.", "required": True},
        "y": {"type": "integer", "description": "Coordonnée Y.", "required": True},
    },
)
def move_mouse(x: int, y: int):
    return _legacy.move_mouse(x, y)


@register_tool(
    name="click_mouse",
    description="Clique aux coordonnées (x, y). Bouton : left, right ou middle.",
    category="Contrôle / Saisie",
    aliases=["mouse_click", "souris_clic", "click"],
    parameters={
        "x": {"type": "integer", "description": "Coordonnée X.", "required": True},
        "y": {"type": "integer", "description": "Coordonnée Y.", "required": True},
        "button": {
            "type": "string",
            "description": "Bouton : left, right ou middle.",
            "required": False,
        },
        "clicks": {
            "type": "integer",
            "description": "Nombre de clics (1=simple, 2=double).",
            "required": False,
        },
    },
)
def click_mouse(x: int, y: int, button: str = "left", clicks: int = 1):
    return _legacy.click_mouse(x, y, button, clicks)


@register_tool(
    name="drag_mouse",
    description="Glisser-déposer de (x1, y1) à (x2, y2).",
    category="Contrôle / Saisie",
    aliases=["mouse_drag", "souris_glisser", "drag", "drag_and_drop"],
    parameters={
        "x1": {"type": "integer", "description": "X début.", "required": True},
        "y1": {"type": "integer", "description": "Y début.", "required": True},
        "x2": {"type": "integer", "description": "X fin.", "required": True},
        "y2": {"type": "integer", "description": "Y fin.", "required": True},
        "duration": {
            "type": "number",
            "description": "Durée du glissement en secondes.",
            "required": False,
        },
    },
)
def drag_mouse(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
    return _legacy.drag_mouse(x1, y1, x2, y2, duration)


@register_tool(
    name="mouse_position",
    description="Récupère la position actuelle de la souris.",
    category="Contrôle / Saisie",
    aliases=["get_mouse_position", "souris_position", "cursor_position"],
)
def mouse_position():
    return _legacy.mouse_position()


@register_tool(
    name="scroll_mouse",
    description="Défilement de la molette (clics positifs = haut, négatifs = bas).",
    category="Contrôle / Saisie",
    aliases=["mouse_scroll", "defiler", "scroll"],
    parameters={
        "clicks": {
            "type": "integer",
            "description": "Crans de défilement (+ haut, - bas).",
            "required": True,
        },
    },
)
def scroll_mouse(clicks: int):
    return _legacy.scroll_mouse(clicks)


# --- Keyboard Tools ---

@register_tool(
    name="type_text",
    description="Tape le texte fourni au clavier.",
    category="Contrôle / Saisie",
    aliases=["taper", "ecrire", "keyboard_type", "write_text"],
    parameters={
        "text": {"type": "string", "description": "Texte à taper.", "required": True},
    },
)
def type_text(text: str):
    return _legacy.type_text(text)


@register_tool(
    name="press_keys",
    description="Appuie sur une combinaison de touches (ex: ctrl+c, alt+tab).",
    category="Contrôle / Saisie",
    aliases=["keyboard_press", "touches", "hotkey", "key_combo"],
    parameters={
        "keys": {
            "type": "string",
            "description": "Touches séparées par + (ex: ctrl+c).",
            "required": True,
        },
    },
)
def press_keys(keys: str):
    return _legacy.press_keys(keys)


# --- Screenshot & OCR ---

@register_tool(
    name="take_screenshot",
    description="Prend une capture d'écran et la sauvegarde dans le dossier courant.",
    category="Contrôle / Saisie",
    aliases=["screenshot", "capture_ecran", "screen_capture", "print_screen"],
)
def take_screenshot():
    return _legacy.take_screenshot()


@register_tool(
    name="extract_text_from_image",
    description="Extrait le texte d'une image via OCR (Tesseract ou OCR PowerShell).",
    category="Contrôle / Saisie",
    aliases=["ocr", "image_to_text", "read_image_text"],
    parameters={
        "image_path": {
            "type": "string",
            "description": "Chemin de l'image à analyser.",
            "required": True,
        },
    },
)
def extract_text_from_image(image_path: str):
    return _legacy.extract_text_from_image(image_path)