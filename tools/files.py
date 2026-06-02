"""
Outils fichiers : lire, écrire, lister, copier, déplacer, supprimer, rechercher, compresser.
"""
from .registry import register_tool
from .decorators import safe_tool
import tools_legacy as _legacy


@register_tool(
    name="read_file",
    description="Lit le contenu d'un fichier texte.",
    category="Fichiers",
    aliases=["file_read", "lire_fichier", "open_file", "cat"],
    parameters={
        "path": {
            "type": "string",
            "description": "Chemin du fichier à lire.",
            "required": True,
        },
    },
)
def read_file(path: str):
    return _legacy.read_file(path)


@register_tool(
    name="write_file",
    description="Écrit ou écrase un fichier avec le contenu fourni.",
    category="Fichiers",
    aliases=["file_write", "ecrire_fichier", "save_file", "create_file"],
    parameters={
        "path": {
            "type": "string",
            "description": "Chemin du fichier.",
            "required": True,
        },
        "content": {
            "type": "string",
            "description": "Contenu à écrire.",
            "required": True,
        },
    },
)
def write_file(path: str, content: str):
    return _legacy.write_file(path, content)


@register_tool(
    name="append_file",
    description="Ajoute du contenu à la fin d'un fichier.",
    category="Fichiers",
    aliases=["file_append", "ajouter_fichier", "append_to_file"],
    parameters={
        "path": {
            "type": "string",
            "description": "Chemin du fichier.",
            "required": True,
        },
        "content": {
            "type": "string",
            "description": "Contenu à ajouter.",
            "required": True,
        },
    },
)
def append_file(path: str, content: str):
    return _legacy.append_file(path, content)


@register_tool(
    name="list_directory",
    description="Liste les fichiers et dossiers d'un répertoire.",
    category="Fichiers",
    aliases=["list_files", "ls", "dir", "lister_dossier", "directory_list"],
    parameters={
        "path": {
            "type": "string",
            "description": "Chemin du dossier ('.' pour dossier courant).",
            "required": False,
        },
        "recursive": {
            "type": "boolean",
            "description": "Lister récursivement ?",
            "required": False,
        },
    },
)
def list_directory(path: str = ".", recursive: bool = False):
    return _legacy.list_directory(path, recursive)


@register_tool(
    name="search_files",
    description="Recherche des fichiers par nom (support wildcards * et ?).",
    category="Fichiers",
    aliases=["find_files", "rechercher_fichiers", "file_search", "locate"],
    parameters={
        "pattern": {
            "type": "string",
            "description": "Motif de recherche (ex: *.py, rapport*).",
            "required": True,
        },
        "directory": {
            "type": "string",
            "description": "Dossier de départ ('.' par défaut).",
            "required": False,
        },
    },
)
def search_files(pattern: str, directory: str = "."):
    return _legacy.search_files(pattern, directory)


@register_tool(
    name="copy_file",
    description="Copie un fichier d'un emplacement à un autre.",
    category="Fichiers",
    aliases=["file_copy", "copier_fichier", "cp"],
    parameters={
        "source": {
            "type": "string",
            "description": "Chemin source.",
            "required": True,
        },
        "destination": {
            "type": "string",
            "description": "Chemin destination.",
            "required": True,
        },
    },
)
def copy_file(source: str, destination: str):
    return _legacy.copy_file(source, destination)


@register_tool(
    name="move_file",
    description="Déplace/renomme un fichier.",
    category="Fichiers",
    aliases=["file_move", "deplacer_fichier", "rename_file", "mv"],
    parameters={
        "source": {
            "type": "string",
            "description": "Chemin source.",
            "required": True,
        },
        "destination": {
            "type": "string",
            "description": "Chemin destination.",
            "required": True,
        },
    },
)
def move_file(source: str, destination: str):
    return _legacy.move_file(source, destination)


@register_tool(
    name="delete_file",
    description="Supprime un fichier.",
    category="Fichiers",
    aliases=["file_delete", "supprimer_fichier", "rm", "remove_file"],
    parameters={
        "path": {
            "type": "string",
            "description": "Chemin du fichier à supprimer.",
            "required": True,
        },
    },
)
def delete_file(path: str):
    return _legacy.delete_file(path)


@register_tool(
    name="create_zip",
    description="Crée une archive ZIP à partir d'un dossier ou fichier.",
    category="Fichiers",
    aliases=["zip", "compress", "compresser", "archive"],
    parameters={
        "source": {
            "type": "string",
            "description": "Chemin source (fichier ou dossier).",
            "required": True,
        },
        "destination": {
            "type": "string",
            "description": "Chemin de l'archive ZIP à créer.",
            "required": True,
        },
    },
)
def create_zip(source: str, destination: str):
    return _legacy.create_zip(source, destination)


@register_tool(
    name="extract_zip",
    description="Extrait une archive ZIP.",
    category="Fichiers",
    aliases=["unzip", "decompresser", "extraire_zip", "uncompress"],
    parameters={
        "zip_path": {
            "type": "string",
            "description": "Chemin de l'archive ZIP.",
            "required": True,
        },
        "destination": {
            "type": "string",
            "description": "Dossier de destination.",
            "required": False,
        },
    },
)
def extract_zip(zip_path: str, destination: str = "."):
    return _legacy.extract_zip(zip_path, destination)


@register_tool(
    name="get_file_info",
    description="Récupère les informations d'un fichier (taille, date, etc.).",
    category="Fichiers",
    aliases=["file_info", "stat", "info_fichier", "file_stat"],
    parameters={
        "path": {
            "type": "string",
            "description": "Chemin du fichier.",
            "required": True,
        },
    },
)
def get_file_info(path: str):
    return _legacy.get_file_info(path)