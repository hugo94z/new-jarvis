import os
import json
import time
import traceback
from openai import OpenAI
import tools
import memory
from personas import build_system_prompt, get_persona, DEFAULT_PERSONA_ID

# Configuration file path
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "wake_word": "ordinateur",
    "tts_voice_id": "",
    "tts_rate": 120,
    "tts_volume": 1.0,
    "memory_enabled": True,
    "persona_id": "jarvis",
    "tts_provider": "edge",
    "tts_edge_voice": "fr-FR-HortenseNeural"
}

def load_config():
    """Load configuration from file, create default if not exists."""
    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG
            
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Ensure all default keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception:
        return DEFAULT_CONFIG

def save_config(config_data):
    """Save configuration to file."""
    try:
        # Load existing first to merge
        current = load_config()
        current.update(config_data)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# List of tools defined for the API
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_screen_resolution",
            "description": "Récupère la résolution actuelle de l'écran (largeur et hauteur en pixels).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot_and_ocr",
            "description": "Prend une capture d'écran de l'ordinateur de l'utilisateur et exécute un OCR local pour renvoyer tous les éléments textuels détectés avec leurs coordonnées spatiales (x, y). Indispensable pour 'voir' l'écran.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_click",
            "description": "Déplace la souris et effectue un clic aux coordonnées spécifiées (x, y).",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Coordonnée X sur l'écran (0 est à gauche)"},
                    "y": {"type": "integer", "description": "Coordonnée Y sur l'écran (0 est en haut)"},
                    "button": {
                        "type": "string", 
                        "enum": ["left", "right"], 
                        "default": "left", 
                        "description": "Bouton de souris à cliquer ('left' pour clic gauche, 'right' pour clic droit)"
                    },
                    "double_click": {
                        "type": "boolean", 
                        "default": False, 
                        "description": "Si défini sur True, effectue un double-clic"
                    }
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_move",
            "description": "Déplace le curseur de la souris aux coordonnées spécifiées (x, y) sans cliquer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Coordonnée X sur l'écran"},
                    "y": {"type": "integer", "description": "Coordonnée Y sur l'écran"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_drag",
            "description": "Glisse la souris depuis sa position actuelle vers les coordonnées spécifiées (x, y) en maintenant le clic gauche enfoncé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Coordonnée X de destination"},
                    "y": {"type": "integer", "description": "Coordonnée Y de destination"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_scroll",
            "description": "Fait défiler la molette de la souris vers le haut ou le bas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string", 
                        "enum": ["up", "down"], 
                        "default": "down", 
                        "description": "Sens du défilement"
                    },
                    "clicks": {
                        "type": "integer", 
                        "default": 3, 
                        "description": "Nombre de crans de défilement"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "keyboard_type",
            "description": "Saisit le texte spécifié comme si l'utilisateur le tapait au clavier. S'exécute à la position actuelle du curseur de texte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Le texte à saisir au clavier"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "keyboard_press",
            "description": "Appuie sur une touche du clavier ou une combinaison de touches. Exemples : 'enter', 'tab', 'win', 'ctrl+c', 'alt+f4', 'ctrl+alt+delete'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "La touche ou combinaison à presser. Utilisez le signe '+' pour les raccourcis complexes."}
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_system_command",
            "description": "Exécute une commande système via PowerShell sur l'ordinateur Windows local et renvoie son résultat (stdout/stderr). Utile pour ouvrir des applications (ex: Start-Process chrome), lister les processus, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "La commande PowerShell à exécuter."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_action",
            "description": "Permet de lire, créer, modifier, supprimer ou lister des fichiers et dossiers locaux.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "append", "delete", "list"],
                        "description": "L'opération à effectuer. 'list' montre les fichiers d'un dossier, 'write' crée ou écrase, 'append' ajoute à la fin."
                    },
                    "path": {"type": "string", "description": "Chemin absolu du fichier ou du dossier."},
                    "content": {
                        "type": "string", 
                        "description": "Contenu textuel pour les actions 'write' ou 'append'."
                    }
                },
                "required": ["action", "path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Met en pause l'exécution pendant un nombre de secondes défini.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "description": "Nombre de secondes d'attente"}
                },
                "required": ["seconds"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Ouvre un site web dans le navigateur par défaut de l'utilisateur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "L'URL complète à ouvrir (ex: https://www.google.com)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Lit le contenu actuel du presse-papier Windows.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_clipboard",
            "description": "Écrit du texte dans le presse-papier Windows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Texte à copier dans le presse-papier"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_window",
            "description": "Récupère le titre et le processus de la fenêtre actuellement active au premier plan.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Récupère les informations système : CPU (%), RAM utilisée (Go), espace disque (Go libre), nom du PC, adresse IP locale.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_info",
            "description": "Stocke une information importante dans la mémoire à long terme de l'assistant pour de futures conversations (préférence utilisateur, fait, tâche en cours, contact).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "L'information à retenir"},
                    "category": {
                        "type": "string",
                        "enum": ["preference", "task", "contact", "fact", "general"],
                        "default": "general",
                        "description": "Catégorie de l'information"
                    },
                    "importance": {
                        "type": "integer",
                        "description": "Importance de 1 (faible) à 10 (critique)",
                        "default": 5
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_info",
            "description": "Recherche dans la mémoire à long terme des informations pertinentes par rapport à une requête. À utiliser avant de répondre à une question personnelle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La requête de recherche"},
                    "top_k": {
                        "type": "integer",
                        "default": 3,
                        "description": "Nombre maximum de résultats à retourner"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["preference", "task", "contact", "fact", "general"],
                        "description": "Filtrer par catégorie (optionnel)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forget_info",
            "description": "Supprime une information de la mémoire à long terme.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer", "description": "ID du souvenir à supprimer"}
                },
                "required": ["memory_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_volume_control",
            "description": "Lit ou modifie le volume système Windows. Utilise 'get' pour connaître le volume actuel, 'set' avec un niveau de 0 à 100 pour le régler, 'mute' pour couper/rétablir le son.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get", "set", "mute"],
                        "default": "get",
                        "description": "Action à effectuer : 'get' (lire), 'set' (modifier), 'mute' (couper/rétablir)"
                    },
                    "level": {
                        "type": "integer",
                        "description": "Niveau de volume (0-100), requis uniquement pour 'set'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Lit le contenu textuel d'un fichier PDF, DOCX ou TXT local. Retourne le texte complet extrait du document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Chemin absolu du fichier à lire (.pdf, .docx, .txt)"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Récupère la météo actuelle d'une ville (température, humidité, vent, description). Utilise wttr.in, service gratuit sans clé API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Nom de la ville (ex: 'Paris', 'Lyon', 'New York')"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Récupère les titres d'actualités récents. Par défaut, actualités générales France. Possibilité de filtrer par sujet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Sujet d'actualité (optionnel, ex: 'technologie', 'sport'). Laissez vide pour actualités générales."},
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Nombre maximum d'articles à retourner (1-10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Envoie une notification popup Windows sur le bureau de l'utilisateur. Utile pour les rappels ou alertes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titre de la notification"},
                    "message": {"type": "string", "description": "Corps du message de la notification"}
                },
                "required": ["title", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Effectue une recherche sur le web via DuckDuckGo et retourne les résultats (titres, URLs, extraits). Sans clé API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La requête de recherche web"},
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Nombre maximum de résultats (1-10)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "switch_tts_voice",
            "description": "Change la voix de synthèse vocale (TTS) de l'assistant en temps réel. Permet de choisir parmi une vingtaine de voix françaises et anglaises (masculines/féminines, accents régionaux). Appelle d'abord get_available_voices si tu ne connais pas les voix disponibles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "voice_id": {"type": "string", "description": "ID exact de la voix Edge TTS (ex: 'fr-FR-DeniseNeural', 'fr-FR-HenriNeural', 'fr-FR-HortenseNeural', 'fr-FR-ClaudeNeural', 'fr-CA-SylvieNeural')"},
                    "gender": {"type": "string", "enum": ["male", "female"], "description": "Genre de voix souhaité : 'male' (masculine) ou 'female' (féminine)"},
                    "accent": {"type": "string", "enum": ["france", "canada", "suisse", "belgique", "anglais_us", "anglais_uk"], "description": "Accent régional souhaité"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_voices",
            "description": "Retourne la liste complète des voix TTS disponibles avec leur ID, description, genre et langue. À utiliser avant switch_tts_voice pour connaître les options.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "download_file",
            "description": "Télécharge un fichier depuis une URL vers le dossier Téléchargements de l'utilisateur. Retourne le chemin complet du fichier téléchargé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL complète du fichier à télécharger (ex: 'https://example.com/fichier.pdf')"},
                    "filename": {"type": "string", "description": "Nom de fichier de destination (optionnel, extrait de l'URL sinon)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cursor_position",
            "description": "Retourne la position actuelle (x, y) du curseur de la souris. Utile pour le debugging, le repérage de coordonnées et les scripts de positionnement.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_archive",
            "description": "Décompresse une archive (ZIP, RAR, 7z) dans un dossier de destination. Supporte ZIP nativement et RAR/7z via 7-Zip si installé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "archive_path": {"type": "string", "description": "Chemin complet vers le fichier archive (.zip, .rar, .7z)"},
                    "dest_folder": {"type": "string", "description": "Dossier de destination (optionnel, créé automatiquement sinon)"}
                },
                "required": ["archive_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Programme un rappel qui déclenche une notification Windows + lecture vocale (TTS) après un délai en secondes. Exemple : 'Rappelle-moi dans 5 minutes de sortir le poulet' → delay_seconds=300.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Le message du rappel (ex: 'Sortir le poulet du four')"},
                    "delay_seconds": {
                        "type": "integer",
                        "default": 60,
                        "description": "Délai avant le rappel en secondes (60 = 1 minute, 300 = 5 minutes, 3600 = 1 heure)"
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "Liste les processus Windows en cours d'exécution avec leur nom, PID, CPU et mémoire. Possibilité de filtrer par nom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "Filtre optionnel par nom de processus (ex: 'chrome', 'python', 'notepad')"},
                    "top": {
                        "type": "integer",
                        "default": 20,
                        "description": "Nombre maximum de processus à retourner (1-50)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kill_process",
            "description": "Ferme (tue) un processus Windows par son nom ou son PID. Utilise taskkill /F. Exemple : fermer Chrome → name='chrome.exe', ou fermer le processus PID 1234 → pid=1234.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nom du processus à fermer (ex: 'notepad.exe', 'chrome.exe')"},
                    "pid": {"type": "integer", "description": "ID numérique du processus à fermer (ex: 1234)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_battery_status",
            "description": "Récupère le niveau de batterie et l'état de charge de l'ordinateur (portables uniquement). Retourne le pourcentage, l'état (charge/décharge/branché) et l'autonomie estimée.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": "Recherche une vidéo YouTube et l'ouvre dans le navigateur par défaut. Ouvre soit la première vidéo directement, soit la page de recherche.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La recherche YouTube (ex: 'musique relaxante', 'tutoriel Python', 'Despacito')"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "text_to_file",
            "description": "Sauvegarde rapidement du texte dans un fichier .txt sur le Bureau de l'utilisateur. Pratique pour prendre des notes, sauvegarder des résultats ou créer des fichiers texte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Nom du fichier (sans extension, .txt ajouté automatiquement). Ex: 'notes_importantes'"},
                    "content": {"type": "string", "description": "Contenu textuel à enregistrer dans le fichier"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Verrouille la session Windows (écran de verrouillage). Équivalent à Win+L.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_computer",
            "description": "Met l'ordinateur en veille.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restart_computer",
            "description": "Redémarre l'ordinateur après un délai (défaut 30 secondes). L'utilisateur peut annuler avec 'shutdown /a'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer", "default": 30, "description": "Délai avant redémarrage en secondes"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_computer",
            "description": "Éteint l'ordinateur après un délai (défaut 60 secondes). L'utilisateur peut annuler avec 'shutdown /a'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer", "default": 60, "description": "Délai avant extinction en secondes"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_wifi_info",
            "description": "Récupère le nom (SSID) et la force du signal du réseau WiFi actuellement connecté.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_bluetooth_devices",
            "description": "Liste les appareils Bluetooth détectés avec leur nom et état.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_installed_apps",
            "description": "Liste les applications installées sur le PC. Possibilité de filtrer par nom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "Filtre optionnel par nom (ex: 'Python', 'Chrome')"},
                    "top": {"type": "integer", "default": 20, "description": "Nombre maximum de résultats"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "Renomme un fichier ou un dossier sur le disque local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin complet du fichier/dossier à renommer"},
                    "new_name": {"type": "string", "description": "Nouveau nom (sans chemin, juste le nom)"}
                },
                "required": ["path", "new_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Déplace un fichier ou un dossier vers une nouvelle destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Chemin source du fichier/dossier"},
                    "destination": {"type": "string", "description": "Chemin de destination (dossier ou fichier)"}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": "Copie un fichier ou un dossier (récursif) vers une nouvelle destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Chemin source du fichier/dossier"},
                    "destination": {"type": "string", "description": "Chemin de destination"}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files_on_disk",
            "description": "Recherche des fichiers par nom sur le disque dur. Retourne les chemins, tailles et dates de modification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Terme de recherche dans le nom du fichier"},
                    "search_path": {"type": "string", "description": "Dossier de départ pour la recherche (défaut: dossier utilisateur)"},
                    "max_results": {"type": "integer", "default": 20, "description": "Nombre maximum de résultats"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_size",
            "description": "Calcule la taille d'un fichier ou d'un dossier (en octets, Ko, Mo ou Go). Retourne aussi le nombre de fichiers si c'est un dossier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier ou dossier"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compress_folder",
            "description": "Compresse un dossier en archive ZIP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {"type": "string", "description": "Chemin du dossier à compresser"},
                    "zip_path": {"type": "string", "description": "Chemin du fichier ZIP de sortie (optionnel)"}
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_music_local",
            "description": "Joue un fichier audio local (MP3, WAV, etc.) avec le lecteur par défaut de Windows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Chemin complet du fichier audio"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_music",
            "description": "Arrête toute lecture audio en cours en fermant les lecteurs connus (Windows Media Player, Spotify, VLC, etc.).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_brightness",
            "description": "Lit ou modifie la luminosité de l'écran (0-100%). Action 'get' pour lire, 'set' pour modifier avec un niveau.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["get", "set"], "default": "get", "description": "'get' pour lire la luminosité, 'set' pour la modifier"},
                    "level": {"type": "integer", "description": "Niveau de luminosité (0-100), requis pour 'set'"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_webcam_photo",
            "description": "Prend une photo avec la webcam et la sauvegarde sur le Bureau. 100% local, aucune donnée envoyée dans le cloud.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Chemin de sauvegarde (optionnel, Bureau par défaut)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_public_ip",
            "description": "Récupère l'adresse IP publique de la connexion Internet.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "speed_test",
            "description": "Effectue un test de débit Internet (téléchargement) et retourne la vitesse estimée en Mbps.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ping_host",
            "description": "Envoie des pings à un hôte (site web, IP) et retourne la latence et le taux de perte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Hôte à pinger (ex: 'google.com', '192.168.1.1')"},
                    "count": {"type": "integer", "default": 4, "description": "Nombre de pings (max 10)"}
                },
                "required": ["host"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dns_lookup",
            "description": "Effectue une résolution DNS d'un nom de domaine et retourne les adresses IP associées.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Nom de domaine (ex: 'google.com')"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_local_network",
            "description": "Scanne le réseau local via ARP pour lister tous les appareils connectés avec leur IP et adresse MAC.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Crée un événement dans le calendrier (fichier .ICS) et l'ouvre pour l'ajouter à Outlook/Calendrier Windows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titre de l'événement"},
                    "date_str": {"type": "string", "description": "Date au format JJ/MM/AAAA ou AAAA-MM-JJ"},
                    "time_str": {"type": "string", "default": "09:00", "description": "Heure de début au format HH:MM"},
                    "duration_minutes": {"type": "integer", "default": 60, "description": "Durée en minutes"},
                    "description": {"type": "string", "default": "", "description": "Description de l'événement"}
                },
                "required": ["title", "date_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_today_events",
            "description": "Récupère les événements du calendrier Outlook du jour (rendez-vous, réunions).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_timer_pomodoro",
            "description": "Lance un minuteur Pomodoro en arrière-plan avec alternance travail/pause. Une notification s'affiche à chaque fin de période.",
            "parameters": {
                "type": "object",
                "properties": {
                    "work_minutes": {"type": "integer", "default": 25, "description": "Durée de travail en minutes"},
                    "break_minutes": {"type": "integer", "default": 5, "description": "Durée de pause en minutes"},
                    "cycles": {"type": "integer", "default": 1, "description": "Nombre de cycles travail+pause"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "encrypt_file",
            "description": "Chiffre ou déchiffre un fichier avec un mot de passe (AES-256). Le fichier chiffré aura l'extension .encrypted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Chemin du fichier à chiffrer/déchiffrer"},
                    "password": {"type": "string", "description": "Mot de passe de chiffrement/déchiffrement"},
                    "action": {"type": "string", "enum": ["encrypt", "decrypt"], "default": "encrypt", "description": "'encrypt' pour chiffrer, 'decrypt' pour déchiffrer"}
                },
                "required": ["filepath", "password"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_browser_cache",
            "description": "Vide le cache des navigateurs web (Chrome, Edge, Firefox) — 100% local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "browser": {"type": "string", "default": "all", "description": "Navigateur : 'chrome', 'edge', 'firefox' ou 'all' pour tous"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_firewall_rules",
            "description": "Affiche les règles actives du pare-feu Windows Defender. Possibilité de filtrer par nom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "Filtre optionnel par nom de règle"},
                    "top": {"type": "integer", "default": 20, "description": "Nombre maximum de règles à afficher"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "qr_code",
            "description": "Génère un QR code PNG à partir de données texte et l'ouvre. 100% local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Données à encoder dans le QR code (texte, URL, etc.)"},
                    "filepath": {"type": "string", "description": "Chemin de sauvegarde du PNG (optionnel, Bureau par défaut)"}
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "qr_reader_from_screenshot",
            "description": "Capture l'écran et lit un QR code visible. Retourne les données décodées. 100% local, 0 cloud.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

# ============================================================================
# Dispatch table — associe un nom de fonction outil à son callable
# Les clés sont les noms des outils, les valeurs sont des tuples (fonction, [liste_args_requises])
# Les lambdas reçoivent fargs (dict des arguments passés par le LLM) et dispatchent vers tools.py
# ============================================================================
FUNCTION_MAP = {
    "get_screen_resolution":    (lambda fargs: tools.get_screen_resolution(), []),
    "take_screenshot_and_ocr":  (lambda fargs: tools.take_screenshot_and_ocr(), []),
    "mouse_click":              (lambda fargs: tools.mouse_click(x=fargs["x"], y=fargs["y"], button=fargs.get("button", "left"), double_click=fargs.get("double_click", False)), ["x", "y"]),
    "mouse_move":               (lambda fargs: tools.mouse_move(x=fargs["x"], y=fargs["y"]), ["x", "y"]),
    "mouse_drag":               (lambda fargs: tools.mouse_drag(x=fargs["x"], y=fargs["y"]), ["x", "y"]),
    "mouse_scroll":             (lambda fargs: tools.mouse_scroll(direction=fargs.get("direction", "down"), clicks=fargs.get("clicks", 3)), []),
    "keyboard_type":            (lambda fargs: tools.keyboard_type(text=fargs["text"]), ["text"]),
    "keyboard_press":           (lambda fargs: tools.keyboard_press(key=fargs["key"]), ["key"]),
    "execute_system_command":   (lambda fargs: tools.execute_system_command(command=fargs["command"]), ["command"]),
    "file_action":              (lambda fargs: tools.file_action(action=fargs["action"], path=fargs["path"], content=fargs.get("content")), ["action", "path"]),
    "wait":                     (lambda fargs: tools.wait(seconds=fargs["seconds"]), ["seconds"]),
    "open_url":                 (lambda fargs: tools.open_url(url=fargs["url"]), ["url"]),
    "get_clipboard":            (lambda fargs: tools.get_clipboard(), []),
    "set_clipboard":            (lambda fargs: tools.set_clipboard(text=fargs["text"]), ["text"]),
    "get_active_window":        (lambda fargs: tools.get_active_window(), []),
    "get_system_info":          (lambda fargs: tools.get_system_info(), []),
    # Nouveaux outils — Amélioration n°8
    "system_volume_control":    (lambda fargs: tools.system_volume_control(action=fargs.get("action", "get"), level=fargs.get("level")), []),
    "read_document":            (lambda fargs: tools.read_document(filepath=fargs["filepath"]), ["filepath"]),
    "get_weather":              (lambda fargs: tools.get_weather(city=fargs["city"]), ["city"]),
    "get_news":                 (lambda fargs: tools.get_news(query=fargs.get("query"), limit=fargs.get("limit", 5)), []),
    "send_notification":        (lambda fargs: tools.send_notification(title=fargs["title"], message=fargs["message"]), ["title", "message"]),
    "web_search":               (lambda fargs: tools.web_search(query=fargs["query"], limit=fargs.get("limit", 5)), ["query"]),
    # Nouveaux outils — Changement de voix TTS
    "switch_tts_voice":         (lambda fargs: tools.switch_tts_voice(voice_id=fargs.get("voice_id"), gender=fargs.get("gender"), accent=fargs.get("accent")), []),
    "get_available_voices":     (lambda fargs: tools.get_available_voices(), []),
    # Nouveaux outils — Extension 9 fonctions
    "download_file":            (lambda fargs: tools.download_file(url=fargs["url"], filename=fargs.get("filename")), ["url"]),
    "get_cursor_position":      (lambda fargs: tools.get_cursor_position(), []),
    "extract_archive":          (lambda fargs: tools.extract_archive(archive_path=fargs["archive_path"], dest_folder=fargs.get("dest_folder")), ["archive_path"]),
    "set_reminder":             (lambda fargs: tools.set_reminder(message=fargs["message"], delay_seconds=fargs.get("delay_seconds", 60)), ["message"]),
    "list_processes":           (lambda fargs: tools.list_processes(filter_name=fargs.get("filter_name"), top=fargs.get("top", 20)), []),
    "kill_process":             (lambda fargs: tools.kill_process(name=fargs.get("name"), pid=fargs.get("pid")), []),
    "get_battery_status":       (lambda fargs: tools.get_battery_status(), []),
    "play_youtube":             (lambda fargs: tools.play_youtube(query=fargs["query"]), ["query"]),
    "text_to_file":             (lambda fargs: tools.text_to_file(filename=fargs["filename"], content=fargs["content"]), ["filename", "content"]),
    # Nouveaux outils — Extension 30 fonctions (système, réseau, fichiers, multimédia, sécurité)
    "lock_screen":              (lambda fargs: tools.lock_screen(), []),
    "sleep_computer":           (lambda fargs: tools.sleep_computer(), []),
    "restart_computer":         (lambda fargs: tools.restart_computer(delay_seconds=fargs.get("delay_seconds", 30)), []),
    "shutdown_computer":        (lambda fargs: tools.shutdown_computer(delay_seconds=fargs.get("delay_seconds", 60)), []),
    "get_wifi_info":            (lambda fargs: tools.get_wifi_info(), []),
    "get_bluetooth_devices":    (lambda fargs: tools.get_bluetooth_devices(), []),
    "get_installed_apps":       (lambda fargs: tools.get_installed_apps(filter_name=fargs.get("filter_name"), top=fargs.get("top", 20)), []),
    "rename_file":              (lambda fargs: tools.rename_file(path=fargs["path"], new_name=fargs["new_name"]), ["path", "new_name"]),
    "move_file":                (lambda fargs: tools.move_file(source=fargs["source"], destination=fargs["destination"]), ["source", "destination"]),
    "copy_file":                (lambda fargs: tools.copy_file(source=fargs["source"], destination=fargs["destination"]), ["source", "destination"]),
    "search_files_on_disk":     (lambda fargs: tools.search_files_on_disk(query=fargs["query"], search_path=fargs.get("search_path"), max_results=fargs.get("max_results", 20)), ["query"]),
    "get_file_size":            (lambda fargs: tools.get_file_size(path=fargs["path"]), ["path"]),
    "compress_folder":          (lambda fargs: tools.compress_folder(folder_path=fargs["folder_path"], zip_path=fargs.get("zip_path")), ["folder_path"]),
    "play_music_local":         (lambda fargs: tools.play_music_local(filepath=fargs["filepath"]), ["filepath"]),
    "stop_music":               (lambda fargs: tools.stop_music(), []),
    "system_brightness":        (lambda fargs: tools.system_brightness(action=fargs.get("action", "get"), level=fargs.get("level")), []),
    "take_webcam_photo":        (lambda fargs: tools.take_webcam_photo(filepath=fargs.get("filepath")), []),
    "get_public_ip":            (lambda fargs: tools.get_public_ip(), []),
    "speed_test":               (lambda fargs: tools.speed_test(), []),
    "ping_host":                (lambda fargs: tools.ping_host(host=fargs["host"], count=fargs.get("count", 4)), ["host"]),
    "dns_lookup":               (lambda fargs: tools.dns_lookup(domain=fargs["domain"]), ["domain"]),
    "scan_local_network":       (lambda fargs: tools.scan_local_network(), []),
    "create_calendar_event":    (lambda fargs: tools.create_calendar_event(title=fargs["title"], date_str=fargs["date_str"], time_str=fargs.get("time_str", "09:00"), duration_minutes=fargs.get("duration_minutes", 60), description=fargs.get("description", "")), ["title", "date_str"]),
    "get_today_events":         (lambda fargs: tools.get_today_events(), []),
    "start_timer_pomodoro":     (lambda fargs: tools.start_timer_pomodoro(work_minutes=fargs.get("work_minutes", 25), break_minutes=fargs.get("break_minutes", 5), cycles=fargs.get("cycles", 1)), []),
    "encrypt_file":             (lambda fargs: tools.encrypt_file(filepath=fargs["filepath"], password=fargs["password"], action=fargs.get("action", "encrypt")), ["filepath", "password"]),
    "clear_browser_cache":      (lambda fargs: tools.clear_browser_cache(browser=fargs.get("browser", "all")), []),
    "show_firewall_rules":      (lambda fargs: tools.show_firewall_rules(filter_name=fargs.get("filter_name"), top=fargs.get("top", 20)), []),
    "qr_code":                  (lambda fargs: tools.qr_code(data=fargs["data"], filepath=fargs.get("filepath")), ["data"]),
    "qr_reader_from_screenshot": (lambda fargs: tools.qr_reader_from_screenshot(), []),
}

# Dispatch table for memory tools — they use self.memory instead of tools.py
MEMORY_FUNCTION_MAP = {
    "remember_info":   (lambda mem, fargs: mem.remember(content=fargs["content"], category=fargs.get("category", "general"), importance=fargs.get("importance", 5)), ["content"]),
    "recall_info":     (lambda mem, fargs: mem.recall(query=fargs["query"], top_k=fargs.get("top_k", 3), category=fargs.get("category")), ["query"]),
    "forget_info":     (lambda mem, fargs: mem.forget(memory_id=fargs["memory_id"]), ["memory_id"]),
}

# Retry configuration for API calls
MAX_API_RETRIES = 5
RETRY_BACKOFF_BASE = 2  # secondes — backoff exponentiel avec jitter: 2s, 4s, 8s, 16s, 32s

# Mapping des erreurs techniques vers des messages utilisateur compréhensibles
ERROR_TRANSLATIONS = {
    "connection": "Impossible de joindre le serveur DeepSeek. Vérifiez votre connexion internet.",
    "timeout": "Le serveur DeepSeek met trop de temps à répondre. Réessayez dans quelques instants.",
    "rate": "Trop de requêtes envoyées au modèle. Patientez quelques secondes avant de réessayer.",
    "quota": "Votre quota API DeepSeek est peut-être épuisé. Vérifiez votre compte.",
    "auth": "Clé API DeepSeek invalide. Vérifiez votre clé dans les paramètres.",
    "api_key": "Clé API DeepSeek invalide ou manquante. Vérifiez votre clé dans les paramètres.",
    "server": "Le serveur DeepSeek rencontre un problème temporaire. Réessayez dans quelques instants.",
    "503": "Le serveur DeepSeek est temporairement indisponible. Réessayez dans un moment.",
    "502": "Le serveur DeepSeek rencontre une erreur interne. Réessayez dans un moment.",
    "504": "Le serveur DeepSeek ne répond pas dans les temps. Réessayez.",
    "500": "Erreur interne du serveur DeepSeek. Réessayez plus tard.",
    "429": "Limite de requêtes atteinte. Patientez quelques secondes avant de réessayer.",
}

def translate_api_error(error_str: str) -> str:
    """Traduit une erreur technique en message utilisateur compréhensible."""
    error_lower = error_str.lower()
    for keyword, message in ERROR_TRANSLATIONS.items():
        if keyword in error_lower:
            return message
    # Message générique si aucun mot-clé ne correspond
    return f"Erreur de communication avec l'IA : {error_str[:200]}"

class Agent:
    def __init__(self, state_callback=None, persona_id=None):
        """
        state_callback: function that accepts (state_name, data) to push updates to frontend.
        persona_id: ID de la personnalité à utiliser (clé dans PERSONAS).
        """
        self.state_callback = state_callback
        self.conversation_history = []
        self.abort_requested = False
        self.memory = memory.MemoryStore()
        self.persona_id = persona_id or DEFAULT_PERSONA_ID

    def update_state(self, state, data=None):
        if self.state_callback:
            try:
                self.state_callback(state, data)
            except Exception as e:
                print(f"Error firing state callback: {e}")

    def abort(self):
        """Request immediate abort of the current agent loop."""
        self.abort_requested = True
        tools.log_action("Interruption de l'agent demandée !")

    def _execute_tool(self, function_name, function_args):
        """Dispatch a tool function call using the dispatch tables.
        Returns the result dict or an error dict."""
        try:
            if function_name in FUNCTION_MAP:
                func, _ = FUNCTION_MAP[function_name]
                return func(function_args)
            elif function_name in MEMORY_FUNCTION_MAP:
                func, _ = MEMORY_FUNCTION_MAP[function_name]
                return func(self.memory, function_args)
            else:
                return {"error": f"Outil '{function_name}' inconnu"}
        except KeyError as ke:
            return {"error": f"Argument manquant pour '{function_name}': {ke}"}
        except Exception as e:
            return {"error": str(e)}

    def _call_llm_with_retry(self, client, config, messages):
        """Calls the LLM API with exponential backoff retry on transient errors."""
        last_error = None
        for attempt in range(MAX_API_RETRIES):
            try:
                return client.chat.completions.create(
                    model=config["model"],
                    messages=messages,
                    tools=AGENT_TOOLS,
                    tool_choice="auto"
                )
            except Exception as api_ex:
                last_error = api_ex
                error_str = str(api_ex).lower()
                is_retriable = any(kw in error_str for kw in [
                    "connect", "timeout", "server", "503", "502", "504", "500", "429", "rate"
                ])
                if is_retriable and attempt < MAX_API_RETRIES - 1:
                    import random
                    wait = (RETRY_BACKOFF_BASE ** (attempt + 1)) + random.uniform(0, 1)
                    tools.log_action(f"API indisponible, nouvelle tentative dans {wait:.1f}s ({attempt + 1}/{MAX_API_RETRIES})...")
                    time.sleep(wait)
                else:
                    raise
        raise last_error or Exception("Échec de toutes les tentatives API")

    def run_query(self, user_query):
        """Runs the main agentic loop for a query."""
        self.abort_requested = False
        config = load_config()
        
        if not config.get("api_key"):
            err_msg = "Clé API DeepSeek non configurée. Veuillez la renseigner dans les paramètres."
            tools.log_action(err_msg)
            self.update_state("ERROR", {"message": err_msg})
            return err_msg

        # Initialize OpenAI compatible client for DeepSeek
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        
        # Add user query to history
        self.conversation_history.append({"role": "user", "content": user_query})
        
        # Build message history for the model
        # Construire le prompt système avec la personnalité choisie
        current_persona_id = config.get("persona_id", self.persona_id)
        system_prompt = build_system_prompt(current_persona_id)
        messages = [{"role": "system", "content": system_prompt}]
        
        # Injection de mémoire pertinente (si activée)
        if config.get("memory_enabled", True):
            try:
                relevant_memories = self.memory.recall(user_query, top_k=3, min_importance=3)
                if relevant_memories.get("results"):
                    mem_context = "📝 **Souvenirs pertinents de l'utilisateur :**\n"
                    for i, mem in enumerate(relevant_memories["results"]):
                        mem_context += f"{i+1}. [{mem['category']}] {mem['content']}\n"
                    messages.append({"role": "system", "content": mem_context})
                    tools.log_action(f"Mémoire : {len(relevant_memories['results'])} souvenirs injectés dans le contexte")
            except Exception as mem_ex:
                tools.log_action(f"Erreur lors de l'injection mémoire: {mem_ex}")
        
        # Limit history to last 15 messages to prevent context bloat
        messages.extend(self.conversation_history[-15:])
        
        self.update_state("THINKING")
        tools.log_action(f"Nouvelle commande reçue : '{user_query}'")

        max_iterations = 50
        iterations = 0
        
        while iterations < max_iterations and not self.abort_requested:
            iterations += 1
            tools.log_action(f"Itération de réflexion de l'agent ({iterations}/{max_iterations})...")
            
            try:
                # Call LLM with retry on transient errors
                response = self._call_llm_with_retry(client, config, messages)
                
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                
                # Check if model wants to call tools
                if tool_calls:
                    # Append model's response (with tool calls) to messages
                    messages.append(response_message)
                    self.conversation_history.append(response_message)
                    
                    self.update_state("EXECUTING")
                    
                    # Execute tools via dispatch table
                    for tool_call in tool_calls:
                        if self.abort_requested:
                            break
                            
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        tools.log_action(f"Appel de l'outil : {function_name}({json.dumps(function_args)})")
                        
                        result = self._execute_tool(function_name, function_args)
                            
                        if "error" in result:
                            tools.log_action(f"Erreur outil {function_name}: {result['error']}")
                            
                        # Format result as JSON string
                        result_str = json.dumps(result)
                        
                        # Add tool response to messages
                        tool_response_msg = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": result_str
                        }
                        messages.append(tool_response_msg)
                        self.conversation_history.append(tool_response_msg)
                        
                    # Loop back to let the LLM think about the tool results
                    self.update_state("THINKING")
                    continue
                else:
                    # Final response from model
                    final_text = response_message.content
                    self.conversation_history.append({"role": "assistant", "content": final_text})
                    
                    self.update_state("SPEAKING", {"text": final_text})
                    tools.log_action(f"Assistant : {final_text}")
                    return final_text
                    
            except Exception as e:
                err_trace = traceback.format_exc()
                print(f"Exception in agent loop: {err_trace}")
                err_msg = f"Erreur lors de la communication avec le modèle : {str(e)}"
                tools.log_action(err_msg)
                self.update_state("ERROR", {"message": err_msg})
                return err_msg

        if self.abort_requested:
            abort_msg = "L'action de l'assistant a été arrêtée par l'utilisateur."
            self.conversation_history.append({"role": "assistant", "content": abort_msg})
            self.update_state("IDLE")
            return abort_msg
            
        timeout_msg = "Le modèle a dépassé le nombre maximal d'itérations autorisées."
        self.conversation_history.append({"role": "assistant", "content": timeout_msg})
        self.update_state("IDLE")
        return timeout_msg
