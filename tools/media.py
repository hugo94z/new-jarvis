"""
Outils média : lecture audio/vidéo, contrôle du lecteur, capture audio, synthèse vocale.
"""
from .registry import register_tool
from .decorators import safe_tool
import tools_legacy as _legacy


@register_tool(
    name="play_media",
    description="Lance la lecture d'un fichier audio ou vidéo avec le lecteur par défaut.",
    category="Média",
    aliases=["play", "jouer", "lire_media", "media_play", "start_media"],
    parameters={
        "file_path": {
            "type": "string",
            "description": "Chemin du fichier audio/vidéo à lire.",
            "required": True,
        },
    },
)
def play_media(file_path: str):
    return _legacy.play_media(file_path)


@register_tool(
    name="stop_media",
    description="Arrête la lecture multimédia en cours.",
    category="Média",
    aliases=["stop", "arreter_media", "media_stop"],
)
def stop_media():
    return _legacy.stop_media()


@register_tool(
    name="pause_media",
    description="Met en pause la lecture multimédia en cours.",
    category="Média",
    aliases=["pause", "media_pause"],
)
def pause_media():
    return _legacy.pause_media()


@register_tool(
    name="resume_media",
    description="Reprend la lecture multimédia après une pause.",
    category="Média",
    aliases=["resume", "reprendre", "media_resume", "unpause"],
)
def resume_media():
    return _legacy.resume_media()


@register_tool(
    name="next_track",
    description="Passe au morceau suivant dans le lecteur.",
    category="Média",
    aliases=["next", "suivant", "skip", "next_song", "morceau_suivant"],
)
def next_track():
    return _legacy.next_track()


@register_tool(
    name="previous_track",
    description="Revient au morceau précédent dans le lecteur.",
    category="Média",
    aliases=["previous", "precedent", "prev", "previous_song", "morceau_precedent"],
)
def previous_track():
    return _legacy.previous_track()


@register_tool(
    name="record_audio",
    description="Enregistre de l'audio depuis le microphone.",
    category="Média",
    aliases=["record", "enregistrer_audio", "audio_record", "microphone"],
    parameters={
        "duration": {
            "type": "integer",
            "description": "Durée de l'enregistrement en secondes.",
            "required": True,
        },
        "save_path": {
            "type": "string",
            "description": "Chemin où sauvegarder l'enregistrement (WAV).",
            "required": False,
        },
    },
)
def record_audio(duration: int, save_path: str = "recording.wav"):
    return _legacy.record_audio(duration, save_path)


@register_tool(
    name="search_spotify",
    description="Recherche et lance un morceau sur Spotify.",
    category="Média",
    aliases=["spotify", "musique", "music", "song", "chanson"],
    parameters={
        "query": {
            "type": "string",
            "description": "Nom du morceau ou de l'artiste.",
            "required": True,
        },
    },
)
def search_spotify(query: str):
    return _legacy.search_spotify(query)


@register_tool(
    name="get_media_info",
    description="Récupère les informations du morceau en cours de lecture.",
    category="Média",
    aliases=["now_playing", "media_info", "current_track", "en_cours"],
)
def get_media_info():
    return _legacy.get_media_info()


# --- Voix / TTS (inclus dans media car lié à l'audio) ---

@register_tool(
    name="switch_tts_voice",
    description="Change la voix de synthèse vocale (ex: 'Microsoft Hortense', 'Microsoft Paul').",
    category="Média",
    aliases=["change_voice", "changer_voix", "tts_voice", "voice"],
    parameters={
        "voice_name": {
            "type": "string",
            "description": "Nom de la voix (filtre sur le nom).",
            "required": True,
        },
    },
)
def switch_tts_voice(voice_name: str):
    return _legacy.switch_tts_voice(voice_name)


@register_tool(
    name="get_available_voices",
    description="Liste toutes les voix TTS installées sur le système.",
    category="Média",
    aliases=["voices", "voix_disponibles", "tts_voices", "list_voices"],
)
def get_available_voices():
    return _legacy.get_available_voices()


VOICE_DESCRIPTIONS = getattr(_legacy, 'VOICE_DESCRIPTIONS', {})