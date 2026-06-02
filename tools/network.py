"""
Outils réseau : requêtes HTTP, météo, IP publique, emails.
"""
from .registry import register_tool
from .decorators import safe_tool
import tools_legacy as _legacy


@register_tool(
    name="http_request",
    description="Effectue une requête HTTP (GET, POST, etc.) et retourne la réponse.",
    category="Réseau",
    aliases=["fetch", "http", "web_request", "api_call", "get_url"],
    parameters={
        "url": {"type": "string", "description": "URL à interroger.", "required": True},
        "method": {
            "type": "string",
            "description": "Méthode HTTP (GET, POST, PUT, DELETE...).",
            "required": False,
        },
        "headers": {
            "type": "string",
            "description": "Headers JSON optionnels.",
            "required": False,
        },
        "body": {
            "type": "string",
            "description": "Corps de la requête (pour POST, PUT...).",
            "required": False,
        },
    },
)
def http_request(url: str, method: str = "GET", headers: str = "", body: str = ""):
    return _legacy.http_request(url, method, headers, body)


@register_tool(
    name="download_file",
    description="Télécharge un fichier depuis une URL.",
    category="Réseau",
    aliases=["download", "telecharger", "fetch_file", "wget"],
    parameters={
        "url": {"type": "string", "description": "URL du fichier.", "required": True},
        "save_path": {
            "type": "string",
            "description": "Chemin où sauvegarder le fichier.",
            "required": True,
        },
    },
)
def download_file(url: str, save_path: str):
    return _legacy.download_file(url, save_path)


@register_tool(
    name="get_public_ip",
    description="Récupère l'adresse IP publique de la machine.",
    category="Réseau",
    aliases=["ip", "public_ip", "external_ip", "my_ip"],
)
def get_public_ip():
    return _legacy.get_public_ip()


@register_tool(
    name="get_weather",
    description="Récupère la météo actuelle pour une ville (en français).",
    category="Réseau",
    aliases=["weather", "meteo", "temperature", "forecast"],
    parameters={
        "city": {
            "type": "string",
            "description": "Nom de la ville.",
            "required": True,
        },
    },
)
def get_weather(city: str):
    return _legacy.get_weather(city)


@register_tool(
    name="send_email",
    description="Envoie un email via SMTP (Gmail).",
    category="Réseau",
    aliases=["email", "mail", "envoyer_email", "send_mail"],
    parameters={
        "to": {
            "type": "string",
            "description": "Adresse du destinataire.",
            "required": True,
        },
        "subject": {
            "type": "string",
            "description": "Sujet de l'email.",
            "required": True,
        },
        "body": {
            "type": "string",
            "description": "Corps de l'email.",
            "required": True,
        },
    },
)
def send_email(to: str, subject: str, body: str):
    return _legacy.send_email(to, subject, body)


@register_tool(
    name="ping_host",
    description="Ping un hôte pour tester la connectivité réseau.",
    category="Réseau",
    aliases=["ping", "test_connection", "network_test"],
    parameters={
        "host": {
            "type": "string",
            "description": "Adresse IP ou nom d'hôte.",
            "required": True,
        },
    },
)
def ping_host(host: str):
    return _legacy.ping_host(host)