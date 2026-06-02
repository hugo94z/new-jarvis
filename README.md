# Assistant Vocal Agentique DeepSeek

> Assistant IA vocal intelligent avec capacités agentiques, multi-personnalités et interface web moderne.

---

## ✨ Fonctionnalités Principales

### 🎭 Multi-Personnalités IA (11 voix/personnalités uniques)
L'assistant peut incarner **11 personnalités différentes**, chacune avec son propre style, ton, prompt système et voix Edge TTS recommandée. Les personnalités disponibles sont :

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

- **Sélecteur rapide** directement depuis le dashboard (cliquer sur le nom de la personnalité active)
- **Grille de sélection visuelle** dans les paramètres
- **Changement automatique de voix** Edge TTS quand on change de personnalité
- **Personnalité par défaut** : Jarvis (configurable)

### 🎙️ Assistant Vocal
- **Synthèse Vocale** : Edge TTS (gratuit, haute qualité) ou SAPI5 (fallback local)
- **Reconnaissance Vocale** : Google Speech Recognition ou PocketSphinx (offline)
- **Wake Word** : Écoute continue avec mot-clé de déclenchement personnalisable par personnalité
- **Mode PTT** : Push-to-talk manuel
- **Visualiseur audio** en temps réel avec animation d'anneau lumineux

### 🧠 Capacités Agentiques
- Connexion API DeepSeek (DeepSeek-V3, DeepSeek-R1) ou compatible OpenAI
- Mode **Agent** : L'IA peut utiliser des outils (recherche web, fichiers, système, etc.)
- Mode **Simple** : Réponses directes sans outils
- **Memory** : Base SQLite pour l'historique des conversations et la mémoire persistante
- **Streaming** : Réponses en temps réel dans l'interface

### 🛠️ Outils Disponibles
L'agent peut utiliser les outils suivants de manière autonome :
- **Système** : Commandes shell, informations système, gestion de processus
- **Fichiers** : Lecture, écriture, listage, recherche dans le système de fichiers
- **Réseau** : Requêtes HTTP, téléchargements, tests de connectivité
- **Web** : Recherche web, scraping, ouverture de navigateur
- **Productivité** : Notes, rappels, minuteurs, calculs
- **Média** : Capture d'écran, lecture audio, OCR
- **Input** : Presse-papiers, captures clavier/souris

### 🎨 Interface Web Moderne
- **Design sombre/clair** avec dégradés et effets de verre (glassmorphism)
- **Dashboard** avec sélecteur de personnalité intégré
- **Chat en streaming** avec support Markdown et coloration syntaxique
- **Paramètres** complets (API, voix, personnalités, thème, historique)
- **Visualiseur audio** animé avec onde sonore
- **Mode responsive** adapté desktop et mobile

### 🔒 Sécurité
- **Arrêt d'urgence** (touche ESC ou bouton)
- Confirmation des actions système dangereuses
- Sandboxing optionnel des commandes shell
- Isolation des outils avec permissions configurables

---

## 🚀 Installation Rapide

### Prérequis
- Python 3.10+ installé
- pip (gestionnaire de paquets Python)
- Connexion Internet pour Edge TTS et l'API DeepSeek

### Installation

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer l'API DeepSeek
# Éditer config.json ou utiliser l'interface web (Paramètres)

# 3. Lancer l'application
python app.py
```

L'application s'ouvre automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8001`.

### Configuration rapide

```json
{
  "api": {
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1",
    "speech_mode": "realtime",
    "temperature": 1.3,
    "max_tokens": 4000
  },
  "agent": {
    "mode": "agent",
    "persona_id": "jarvis"
  },
  "voice": {
    "engine": "edge",
    "edge_voice": "fr-FR-HenriNeural",
    "language": "fr-FR"
  },
  "tools": {
    "allowed": ["system", "files", "network", "web", "productivity", "media", "input"]
  }
}
```

---

## 🎭 Utilisation des Personnalités

### Depuis le Dashboard
1. Cliquer sur le **sélecteur de personnalité** (affiche le nom et l'icône de la personnalité active)
2. Un menu déroulant apparaît avec toutes les personnalités disponibles
3. Sélectionner une personnalité → la voix Edge TTS recommandée est automatiquement appliquée
4. La personnalité est sauvegardée immédiatement

### Depuis les Paramètres
1. Aller dans l'onglet **Paramètres** (⚙️)
2. Faire défiler jusqu'à la section **"Personnalité de l'IA"**
3. Choisir parmi la grille de cartes visuelles
4. La voix Edge TTS recommandée s'ajuste automatiquement
5. Cliquer sur **"Appliquer"** pour sauvegarder

### Personnalisation
- Chaque personnalité a un **prompt système** unique définissant son style et son ton
- Les prompts sont dans `personas.py` et peuvent être modifiés
- La **voix Edge TTS recommandée** est liée à chaque personnalité
- Le **mot-clé de déclenchement** (wake word) est suggéré selon la personnalité

---

## 📁 Structure du Projet

```
.
├── app.py                 # Serveur FastAPI + WebSocket + API REST
├── agent.py               # Agent IA (DeepSeek, OpenAI compatible)
├── voice.py               # Gestion voix (Edge TTS + SAPI5) et reconnaissance vocale
├── tools.py               # Définition des outils disponibles
├── memory.py              # Gestion mémoire SQLite (conversations, souvenirs)
├── personas.py            # Définition des 11 personnalités IA
├── config.json            # Configuration utilisateur
├── requirements.txt       # Dépendances Python
├── run_assistant.bat      # Script de lancement Windows
├── static/
│   ├── index.html         # Interface web (dashboard, chat, paramètres)
│   ├── app.js             # Logique frontend (WebSocket, UI, personnalités)
│   └── styles.css         # Styles CSS (design system, animations)
└── memory.db              # Base de données SQLite (auto-générée)
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

---

## 📄 Licence

Projet personnel - Usage libre.

---

**DeepSeek Agentic Voice Assistant** — *v2.1 — Multi-Personnalités*