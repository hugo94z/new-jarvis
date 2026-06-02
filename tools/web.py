"""
Outils web : ouvrir navigateur, YouTube, recherche Google, raccourcis.
"""
from .registry import register_tool
from .decorators import safe_tool
import tools_legacy as _legacy


@register_tool(
    name="open_browser",
    description="Ouvre le navigateur par défaut sur une URL ou page blanche.",
    category="Web",
    aliases=["browser", "navigateur", "open_url", "start_browser"],
    parameters={
        "url": {
            "type": "string",
            "description": "URL à ouvrir (vide pour page d'accueil).",
            "required": False,
        },
        "browser": {
            "type": "string",
            "description": "Navigateur spécifique (chrome, firefox, edge).",
            "required": False,
        },
    },
)
def open_browser(url: str = "", browser: str = ""):
    return _legacy.open_browser(url, browser)


@register_tool(
    name="search_youtube",
    description="Recherche des vidéos sur YouTube.",
    category="Web",
    aliases=["youtube", "yt", "video_search", "recherche_video"],
    parameters={
        "query": {
            "type": "string",
            "description": "Termes de recherche.",
            "required": True,
        },
    },
)
def search_youtube(query: str):
    return _legacy.search_youtube(query)


@register_tool(
    name="search_google",
    description="Effectue une recherche sur Google.",
    category="Web",
    aliases=["google", "recherche", "search", "web_search", "recherche_web"],
    parameters={
        "query": {
            "type": "string",
            "description": "Termes de recherche.",
            "required": True,
        },
    },
)
def search_google(query: str):
    return _legacy.search_google(query)


@register_tool(
    name="search_wikipedia",
    description="Recherche un article sur Wikipédia et retourne un résumé.",
    category="Web",
    aliases=["wikipedia", "wiki", "encyclopedia", "encyclopedie"],
    parameters={
        "query": {
            "type": "string",
            "description": "Sujet de recherche.",
            "required": True,
        },
        "lang": {
            "type": "string",
            "description": "Code langue (fr, en, etc.). Défaut: fr.",
            "required": False,
        },
    },
)
def search_wikipedia(query: str, lang: str = "fr"):
    return _legacy.search_wikipedia(query, lang)


@register_tool(
    name="open_site_shortcut",
    description="Ouvre un site web connu par son nom (ex: gmail, drive, github, twitter, linkedin...).",
    category="Web",
    aliases=["shortcut", "raccourci_web", "ouvrir_site", "open_site"],
    parameters={
        "site_name": {
            "type": "string",
            "description": "Nom court du site (gmail, drive, github, twitter, linkedin, whatsapp, messenger, instagram, netflix, spotify, amazon, twitch, discord, reddit, stackoverflow).",
            "required": True,
        },
    },
)
def open_site_shortcut(site_name: str):
    return _legacy.open_site_shortcut(site_name)


@register_tool(
    name="get_trending_topics",
    description="Récupère les sujets tendance (via Google Trends ou Twitter).",
    category="Web",
    aliases=["trends", "trending", "tendances", "actu", "actualites"],
)
def get_trending_topics():
    return _legacy.get_trending_topics()


@register_tool(
    name="translate_text",
    description="Traduit un texte dans une autre langue (via Google Translate).",
    category="Web",
    aliases=["translate", "traduire", "traduction", "translation"],
    parameters={
        "text": {
            "type": "string",
            "description": "Texte à traduire.",
            "required": True,
        },
        "target_lang": {
            "type": "string",
            "description": "Code langue cible (fr, en, es, de...). Défaut: fr.",
            "required": False,
        },
        "source_lang": {
            "type": "string",
            "description": "Code langue source (auto par défaut).",
            "required": False,
        },
    },
)
def translate_text(text: str, target_lang: str = "fr", source_lang: str = "auto"):
    return _legacy.translate_text(text, target_lang, source_lang)