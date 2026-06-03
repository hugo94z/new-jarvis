# Assistant Vocal Agentique DeepSeek

> Assistant IA vocal intelligent avec capacités agentiques, multi-personnalités et interface web moderne.

---

## ⚡ Deux Façons d'Utiliser l'Application

| Méthode | Description | Pour qui ? |
|---------|------------|------------|
| **Fichier .exe** | `Installer_NouveauDossier13.exe` (19 Mo) — exécutable standalone généré avec PyInstaller contenant Python 3.12 + toutes les dépendances | Utilisateurs qui veulent lancer l'appli sans rien installer |
| **Code source** | `python app.py` avec `pip install -r requirements.txt` | Développeurs ou utilisateurs avancés |

> **Important :** Même avec le `.exe`, certains composants **externes** doivent être installés manuellement :
> - **Tesseract OCR** (pour la fonction OCR/capture d'écran)
> - **ffmpeg** (optionnel, pour la détection de durée audio via Edge TTS)
> - Voir [Prérequis Externes](#-prérequis-externes-non-installables-via-pip) ci-dessous.

---

## ✨ Fonctionnalités Principales

### 🎭 Multi-Personnalités IA (11 voix/personnalités uniques)
L'assistant peut incarner **11 personnalités différentes**, chacune avec son propre style, ton, prompt système et voix Edge TTS recommandée :

| ID | Icône | Nom | Description | Voix Recommandée | Mot-Clé |
|----|-------|-----|-------------|-------------------|---------|
| `jarvis` | 🤖 | **Jarvis** | Assistant professionnel, concis et efficace | `fr-FR-HenriNeural` | jarvis |
| `hortense` | 🌸 | **Hortense** | Assistante chaleureuse et bienveillante | `fr-FR-HortenseNeural` | hortense |
| `claude` | 🧠 | **Claude** | Expert technique, précis et analytique | `fr-FR-ClaudeNeural` | claude |
| `celeste` | ✨ | **Céleste** | Assistante poétique, créative et rêveuse | `fr-FR-CelesteNeural` | céleste |
| `denise` | ⚡ | **Denise** | Assistante dynamique, énergique et motivante | `fr-FR-DeniseNeural` | denise |
| `alain` | 😎 | **Alain** | Assistant décontracté, amical et plein d'humour | `fr-FR-AlainNeural` | alain |
| `antoine` | 🍁 | **Antoine** | Assistant au charme canadien, poli et serviable | `fr-CA-AntoineNeural` | antoine |
| `ariane` | 🏔️ | **Ariane** | Assistante suisse, précise et méthodique | `fr-CH-ArianeNeural` | ariane |
| `remy` | 🌍 | **Rémy** | Assistant multilingue, ouvert sur le monde | `fr-FR-RemyMultilingualNeural` | rémy |
| `charline` | 🍫 | **Charline** | Assistante belge, conviviale et gourmande | `fr-BE-CharlineNeural` | charline |
| `sylvie` | 💜 | **Sylvie** | Assistante canadienne douce et empathique | `fr-CA-SylvieNeural` | sylvie |

### 🎙️ Assistant Vocal
- **Synthèse Vocale** : Edge TTS (gratuit, haute qualité) ou SAPI5 (fallback local Windows)
- **Reconnaissance Vocale** : Google Speech Recognition ou PocketSphinx (offline)
- **Wake Word** : Écoute continue avec mot-clé de déclenchement personnalisable par personnalité
- **Mode PTT** : Push-to-talk manuel
- **Visualiseur audio** en temps réel avec animation d'anneau lumineux

### 🧠 Capacités Agentiques
- Connexion API DeepSeek (DeepSeek-V3, DeepSeek-R1) ou compatible OpenAI
- Mode **Agent** : L'IA utilise des outils (recherche web, fichiers, système, etc.)
- **Memory** : Base SQLite pour historique des conversations et mémoire persistante
- **Streaming** : Réponses en temps réel via WebSocket

### 🛠️ Outils Disponibles (50+ fonctions)
- **Système** : Commandes shell, informations système, processus, WiFi, Bluetooth
- **Fichiers** : Lecture, écriture, copie, déplacement, compression, chiffrement
- **Réseau** : Ping, DNS, scan réseau, IP publique, speed test
- **Web** : Recherche web, ouverture navigateur, YouTube
- **Productivité** : Notes, rappels, minuteurs, calendrier, notifications
- **Média** : Capture d'écran, OCR, webcam, QR code, musique
- **Input** : Presse-papiers, contrôle souris/clavier, fenêtres

---

## 📋 Prérequis Externes (non installables via pip)

Avant toute utilisation, ces logiciels doivent être installés **manuellement** :

| Logiciel | Pour quelle fonction ? | Lien de téléchargement | Obligatoire ? |
|----------|----------------------|------------------------|---------------|
| **Python 3.10+** | Code source uniquement (pas besoin avec .exe) | https://python.org | Pour code source |
| **Tesseract OCR 5.x** | OCR (capture d'écran → texte) | https://github.com/UB-Mannheim/tesseract/wiki | Recommandé |
| **ffmpeg** | Edge TTS (détection durée audio) | https://ffmpeg.org/download.html | Optionnel |
| **7-Zip** | Décompression RAR/7z | https://7-zip.org/ | Optionnel |
| **Visual Studio Build Tools** | Compilation PyAudio | Via Visual Studio Installer | Optionnel (alternatives) |

### Installation de Tesseract OCR
```bash
# 1. Télécharger et installer depuis :
#    https://github.com/UB-Mannheim/tesseract/wiki
# 2. Choisir "French" pendant l'installation pour le support du français
# 3. Après installation, vérifier :
tesseract --version
```

---

## 🚀 Installation Complète

### Méthode 1 : Avec le fichier .exe (recommandé)

```bash
# 1. Double-cliquer sur Installer_NouveauDossier13.exe
#    (ou lancer depuis un terminal)
Installer_NouveauDossier13.exe

# 2. Configurer la clé API DeepSeek
#    Créer/éditer config.json dans le même dossier :
{
    "api_key": "sk-votre-cle-api-deepseek",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
}

# 3. Installer Tesseract OCR (optionnel mais recommandé)
#    Voir section "Prérequis Externes"
```

### Méthode 2 : Développement avec code source

```bash
# 1. Cloner le projet
git clone https://github.com/hugo94z/Nouveau-dossier--13-.git
cd "Nouveau dossier (13)"

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv
venv\Scripts\activate

# 3. Installer les dépendances Python
pip install -r requirements.txt

# ⚠️ Si PyAudio échoue (erreur de compilation), utiliser :
# pip install pipwin
# pipwin install pyaudio

# 4. Configurer la clé API DeepSeek
#    Éditer config.json et ajouter votre clé API

# 5. Lancer l'application
python app.py
#   ou double-cliquer sur run_assistant.bat
```

L'application s'ouvre automatiquement dans votre navigateur à l'adresse : **http://localhost:8000**

---

## ⚙️ Configuration

### config.json — Référence Complète

```json
{
    "api_key": "sk-votre-cle-api-deepseek",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "wake_word": "jarvis",
    "persona_id": "jarvis",
    "tts_provider": "edge",
    "tts_voice_id": "",
    "tts_edge_voice": "fr-FR-HenriNeural",
    "tts_rate": 120,
    "tts_volume": 1,
    "language": "fr-FR",
    "speech_mode": "realtime",
    "temperature": 1.3,
    "max_tokens": 4000,
    "memory_enabled": true
}
```

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `api_key` | `sk-...` | **OBLIGATOIRE** — Clé API DeepSeek |
| `base_url` | URL | URL de l'API (DeepSeek ou compatible OpenAI) |
| `model` | `deepseek-chat` | Modèle (`deepseek-chat`, `deepseek-reasoner`) |
| `wake_word` | `"jarvis"` | Mot de déclenchement vocal |
| `persona_id` | `"jarvis"` | Personnalité par défaut (voir tableau des 11 personnalités) |
| `tts_provider` | `"edge"` | Moteur TTS : `"edge"` (gratuit) ou `"pyttsx3"` (SAPI5 local) |
| `tts_edge_voice` | `"fr-FR-HenriNeural"` | Voix Edge TTS (voir tableau des personnalités) |
| `tts_rate` | `120` | Vitesse de parole (100 = normal, <100 plus lent, >100 plus rapide) |
| `tts_volume` | `1` | Volume (0.0 à 1.0) |
| `temperature` | `1.3` | Créativité du modèle (0.0 = précis, 2.0 = créatif) |
| `max_tokens` | `4000` | Longueur maximale des réponses |
| `memory_enabled` | `true` | Activer la mémoire vectorielle (nécessite `sentence-transformers`) |

### Obtenir une clé API DeepSeek
1. Aller sur https://platform.deepseek.com
2. Créer un compte (numéro de téléphone requis)
3. Aller dans **API Keys** → Créer une nouvelle clé
4. Copier la clé dans `config.json`

---

## 🔧 Dépannage (Troubleshooting)

### PyAudio / PyWin ne s'installe pas
```bash
# Erreur : Microsoft Visual C++ 14.0 or greater is required
# Solution 1 : pipwin (recommandé)
pip install pipwin
pipwin install pyaudio

# Solution 2 : Installer Visual Studio Build Tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Puis réessayer : pip install pyaudio
```

### Le .exe ne se lance pas
```bash
# Vérifier que tous les fichiers sont dans le même dossier :
# - Installer_NouveauDossier13.exe
# - config.json (doit être créé manuellement)
# - static/ (dossier avec index.html, app.js, styles.css)

# Problèmes courants :
# 1. Windows SmartScreen bloque → cliquer "Informations complémentaires" → "Exécuter quand même"
# 2. Port 8000 déjà utilisé → fermer l'autre application
```

### TTS Edge ne fonctionne pas
```bash
# Vérifier la connexion Internet (Edge TTS nécessite Internet)
# Fallback automatique vers SAPI5 (voix Windows locales)
# Vérifier que edge-tts est installé :
pip install edge-tts

# Si "ffprobe not found" : installer ffmpeg
# https://ffmpeg.org/download.html
```

### OCR (capture d'écran) ne fonctionne pas
```bash
# Vérifier que Tesseract est installé :
tesseract --version

# Si non trouvé, installer depuis :
# https://github.com/UB-Mannheim/tesseract/wiki
# Puis redémarrer l'application
```

### Les dépendances manquent dans le .exe
```bash
# Le .exe contient TOUTES les dépendances nécessaires
# Sauf : Tesseract OCR, ffmpeg, 7-Zip (logiciels système)
# Si une fonction ne marche pas, vérifier que le logiciel requis est installé
```

---

## 📁 Structure du Projet

```
.
├── Installer_NouveauDossier13.exe  # Exécutable standalone (19 Mo)
├── app.py                          # Serveur FastAPI + WebSocket + API REST
├── agent.py                        # Agent IA (DeepSeek, OpenAI compatible)
├── voice.py                        # Gestion voix (Edge TTS + SAPI5) et reconnaissance vocale
├── memory.py                       # Gestion mémoire SQLite (conversations, souvenirs)
├── personas.py                     # Définition des 11 personnalités IA
├── config.json                     # Configuration utilisateur (clé API, voix, etc.)
├── requirements.txt                # Dépendances Python (pour le développement)
├── run_assistant.bat               # Script de lancement Windows
├── ocr.ps1                         # Script PowerShell pour OCR
├── tools/                          # Modules d'outils
│   ├── __init__.py
│   ├── registry.py                 # Registre des outils
│   ├── decorators.py
│   ├── system.py                   # Outils système
│   ├── files.py                    # Outils fichiers
│   ├── network.py                  # Outils réseau
│   ├── web.py                      # Outils web
│   ├── productivity.py             # Outils productivité
│   ├── media.py                    # Outils média
│   └── input_tools.py              # Outils d'entrée (souris, clavier)
├── static/
│   ├── index.html                  # Interface web (dashboard, chat, paramètres)
│   ├── app.js                      # Logique frontend (WebSocket, UI, personnalités)
│   └── styles.css                  # Styles CSS (design system, animations)
└── memory.db                       # Base de données SQLite (auto-générée)
```

---

## 🛠️ Technologies Utilisées

| Composant | Technologie |
|-----------|-------------|
| **Backend** | Python 3.10+, FastAPI, WebSocket |
| **IA** | DeepSeek API (V3, R1), compatible OpenAI |
| **Voix** | Edge TTS (gratuit), SAPI5 (Windows fallback) |
| **Reconnaissance Vocale** | Google Speech Recognition, PocketSphinx |
| **Base de données** | SQLite (via `sqlite3`) |
| **Frontend** | HTML5, CSS3, JavaScript vanilla |
| **Streaming** | Server-Sent Events via WebSocket |
| **Audio** | PyAudio, wave, pydub |
| **Emballage** | PyInstaller (pour le .exe) |

---

## 🔧 Commandes Clavier

| Touche | Action |
|--------|--------|
| `ESC` | **Arrêt d'urgence** (stoppe toute action en cours) |
| `Ctrl+Entrée` | Envoyer le message |
| `Espace` (maintenu) | Push-to-talk (mode PTT) |

---

## 📝 Développement

### Ajouter une nouvelle personnalité

Éditer `personas.py` et ajouter une entrée dans la liste `PERSONAS` :

```python
{
    "id": "mon_perso",
    "name": "Mon Perso",
    "description": "Description courte pour l'UI",
    "icon": "🦊",
    "system_prompt_extra": """Tu incarnes Mon Perso...
Ton style :
- Point 1
- Point 2""",
    "recommended_edge_voice": "fr-FR-MaVoixNeural",
    "wake_word_suggestion": "mon perso"
},
```

La nouvelle personnalité apparaîtra automatiquement dans l'interface.

### Recompiler le .exe avec PyInstaller
```bash
pip install pyinstaller
pyinstaller --onefile --name Installer_NouveauDossier13 --add-data "static;static" app.py
```

---

## 📄 Licence

Projet personnel - Usage libre.

---

**DeepSeek Agentic Voice Assistant** — *v2.2 — Multi-Personnalités*