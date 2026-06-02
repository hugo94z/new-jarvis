import sys
import threading
import queue
import time
import asyncio
import tempfile
import os
import subprocess
import speech_recognition as sr

# Try importing pyttsx3
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

# Try importing edge-tts
try:
    import edge_tts
except ImportError:
    edge_tts = None

# Liste des voix Edge TTS françaises disponibles (gratuites, haute qualité)
EDGE_FRENCH_VOICES = [
    {"id": "fr-FR-HenriNeural", "name": "Henri", "gender": "Homme", "language": "fr-FR"},
    {"id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "Femme", "language": "fr-FR"},
    {"id": "fr-FR-HortenseNeural", "name": "Hortense", "gender": "Femme", "language": "fr-FR"},
    {"id": "fr-FR-CelesteNeural", "name": "Céleste", "gender": "Femme", "language": "fr-FR"},
    {"id": "fr-FR-ClaudeNeural", "name": "Claude", "gender": "Homme", "language": "fr-FR"},
    {"id": "fr-FR-AlainNeural", "name": "Alain", "gender": "Homme", "language": "fr-FR"},
    {"id": "fr-FR-VivienneMultilingualNeural", "name": "Vivienne (Multilingue)", "gender": "Femme", "language": "fr-FR"},
    {"id": "fr-FR-RemyMultilingualNeural", "name": "Rémy (Multilingue)", "gender": "Homme", "language": "fr-FR"},
    {"id": "fr-CA-AntoineNeural", "name": "Antoine (Canadien)", "gender": "Homme", "language": "fr-CA"},
    {"id": "fr-CA-JeanNeural", "name": "Jean (Canadien)", "gender": "Homme", "language": "fr-CA"},
    {"id": "fr-CA-SylvieNeural", "name": "Sylvie (Canadienne)", "gender": "Femme", "language": "fr-CA"},
    {"id": "fr-CH-ArianeNeural", "name": "Ariane (Suisse)", "gender": "Femme", "language": "fr-CH"},
    {"id": "fr-CH-FabriceNeural", "name": "Fabrice (Suisse)", "gender": "Homme", "language": "fr-CH"},
    {"id": "fr-BE-CharlineNeural", "name": "Charline (Belge)", "gender": "Femme", "language": "fr-BE"},
    {"id": "fr-BE-GerardNeural", "name": "Gérard (Belge)", "gender": "Homme", "language": "fr-BE"},
]

# Quelques voix anglaises populaires pour compléter
EDGE_EXTRA_VOICES = [
    {"id": "en-US-AriaNeural", "name": "Aria (US)", "gender": "Femme", "language": "en-US"},
    {"id": "en-US-GuyNeural", "name": "Guy (US)", "gender": "Homme", "language": "en-US"},
    {"id": "en-US-JennyNeural", "name": "Jenny (US)", "gender": "Femme", "language": "en-US"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "gender": "Femme", "language": "en-GB"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (UK)", "gender": "Homme", "language": "en-GB"},
]

class VoiceManager:
    def __init__(self, voice_id=None, rate=120, volume=1.0, tts_provider="pyttsx3", edge_voice="fr-FR-HortenseNeural"):
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.tts_thread = None
        self.stop_speech_event = threading.Event()
        
        self.voice_id = voice_id
        try:
            self.rate = int(rate)
        except (TypeError, ValueError):
            self.rate = 120
        self.volume = volume
        self.tts_provider = tts_provider  # "pyttsx3" or "edge"
        self.edge_voice = edge_voice  # Voix Edge TTS sélectionnée
        
        # Initialize pyttsx3 in the main thread if possible, or we will initialize it inside the speech thread
        # pyttsx3 requires initializing in the same thread it speaks on for some drivers
        self.engine = None
        self._init_tts_engine()

        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300
        self.microphone = None
        
        # Background listening handles
        self.stop_background_listen_fn = None
        self.bg_listening_active = False
        
        # Conversation mode (post wake-word)
        self.conversation_mode_active = False
        self.conversation_timer = None
        self.on_conversation_timeout = None  # Callback when conversation mode expires
        
        # Paramètres du listener unifié (pour éviter stop/restart)
        self._wake_word = None
        self._on_wake_callback = None
        self._listener_started = False
        
        # Callbacks
        self.on_conversation_speech = None  # Set by app.py
        self.on_speech_done = None  # Set by app.py
        
        # Démarrer le worker TTS dans son propre thread (obligatoire pour pyttsx3/SAPI5 sur Windows)
        self._start_tts_worker()

    def _start_tts_worker(self):
        """Start the TTS worker thread."""
        if pyttsx3 is None:
            print("[TTS] pyttsx3 not available, TTS disabled.")
            return
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()
        print("[TTS] Worker thread démarré.")

    def _init_tts_engine(self):
        if pyttsx3 is None:
            print("WARNING: pyttsx3 is not installed. TTS will be disabled.")
            return
        
        try:
            # We initialize it once to query voices or verify
            self.engine = pyttsx3.init()
            if self.voice_id:
                try:
                    self.engine.setProperty('voice', self.voice_id)
                except Exception:
                    pass
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
        except Exception as e:
            print(f"WARNING: Failed to initialize pyttsx3 engine: {e}")
            self.engine = None

    def get_voices(self):
        """Returns list of available system voices."""
        if not self.engine:
            # Try initializing temporary engine
            try:
                temp_engine = pyttsx3.init()
                voices = temp_engine.getProperty('voices')
                return [{"id": v.id, "name": v.name, "languages": v.languages} for v in voices]
            except Exception:
                return []
        
        try:
            voices = self.engine.getProperty('voices')
            return [{"id": v.id, "name": v.name, "languages": v.languages} for v in voices]
        except Exception:
            return []

    def set_voice(self, voice_id):
        self.voice_id = voice_id
        if self.engine:
            try:
                self.engine.setProperty('voice', voice_id)
            except Exception:
                pass

    def set_rate(self, rate):
        try:
            self.rate = int(rate)
        except (TypeError, ValueError):
            self.rate = 120
        if self.engine:
            try:
                self.engine.setProperty('rate', self.rate)
            except Exception:
                pass

    def _normalize_text(self, text: str) -> str:
        """Nettoie le markdown, ajoute des pauses, supprime les emojis pour un TTS plus naturel."""
        import re
        
        # Supprimer les blocs de code
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Supprimer le markdown inline
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.*?)\*', r'\1', text)       # *italic*
        text = re.sub(r'__(.*?)__', r'\1', text)       # __bold__
        text = re.sub(r'_(.*?)_', r'\1', text)         # _italic_
        text = re.sub(r'`([^`]*)`', r'\1', text)       # `code`
        text = re.sub(r'~~(.*?)~~', r'\1', text)       # ~~strike~~
        # Supprimer les titres markdown
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Supprimer les liens [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Supprimer les images ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
        # Supprimer les listes
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        # Supprimer les blockquotes
        text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
        # Supprimer les lignes horizontales
        text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        # Supprimer les emojis
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
                      r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
                      r'\U00002702-\U000027B0\U000024C2-\U0001F251'
                      r'\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F'
                      r'\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
                      r'\U0000FE00-\U0000FE0F\u200d\u2600-\u26FF\u2700-\u27BF]+',
                      '', text)
        # Supprimer les séquences de sauts de ligne multiples
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remplacer les points par point + double espace pour créer des pauses
        text = re.sub(r'\.(\s+)', r'.  \1', text)
        text = re.sub(r'\?(\s+)', r'?  \1', text)
        text = re.sub(r'!(\s+)', r'!  \1', text)
        # Remplacer les deux-points par une pause légère
        text = re.sub(r':(\s+)(?=[A-Z])', r':  \1', text)
        # Supprimer les espaces multiples excessifs
        text = re.sub(r' {3,}', '  ', text)
        # Nettoyer les lignes vides
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Strip
        text = text.strip()
        
        return text

    def _tts_worker(self):
        """Worker thread for speaking text sequentially."""
        print("[TTS Worker] Démarrage du worker TTS...")
        
        # Initialize COM for this thread on Windows
        if sys.platform == 'win32':
            import ctypes
            try:
                hr = ctypes.windll.ole32.CoInitialize(None)
                print(f"[TTS Worker] COM CoInitialize: HRESULT={hr}")
            except Exception as e:
                print(f"[TTS Worker] Error initializing COM: {e}")

        # Initialize an engine inside the thread (pyttsx3 is thread-sensitive)
        local_engine = None
        try:
            print(f"[TTS Worker] Initialisation pyttsx3 avec voice_id='{self.voice_id}', rate={self.rate}, volume={self.volume}")
            local_engine = pyttsx3.init()
            voices = local_engine.getProperty('voices')
            voice_names = [v.name for v in voices]
            print(f"[TTS Worker] {len(voices)} voix système trouvées: {voice_names}")
            
            if self.voice_id:
                try:
                    local_engine.setProperty('voice', self.voice_id)
                    print(f"[TTS Worker] Voix définie: {self.voice_id}")
                except Exception as ve:
                    print(f"[TTS Worker] Impossible de définir la voix '{self.voice_id}': {ve}. Utilisation de la voix par défaut.")
                    # Ne pas planter, continuer avec la voix par défaut
            else:
                print("[TTS Worker] Aucune voix spécifique configurée, utilisation de la voix par défaut")
                
            local_engine.setProperty('rate', self.rate)
            local_engine.setProperty('volume', self.volume)
            print(f"[TTS Worker] Engine pyttsx3 initialisé avec succès")
        except Exception as e:
            print(f"[TTS Worker] ERREUR FATALE init pyttsx3: {e}")
            import traceback
            traceback.print_exc()
            self.is_speaking = False
            return

        self.is_speaking = True
        print("[TTS Worker] Boucle principale démarrée, en attente de texte dans la queue...")
        
        while not self.stop_speech_event.is_set():
            try:
                # Wait for text to speak
                text = self.speech_queue.get(timeout=0.1)
                
                # Check if stop event was set while waiting
                if self.stop_speech_event.is_set():
                    break
                
                # Speak
                print(f"[TTS Worker] Prononciation: '{text[:60]}...' ({len(text)} chars)")
                local_engine.say(text)
                
                # We need to run loop to actually speak
                local_engine.runAndWait()
                print(f"[TTS Worker] Prononciation terminée")
                self.speech_queue.task_done()
                
                # Trigger callback if queue is empty (finished speaking current block)
                if self.speech_queue.empty():
                    print("[TTS Worker] Queue vide après prononciation")
                    if hasattr(self, 'on_speech_done') and self.on_speech_done:
                        try:
                            self.on_speech_done()
                        except Exception as e:
                            print(f"Error in on_speech_done callback: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS Worker] ERREUR dans la boucle TTS: {e}")
                import traceback
                traceback.print_exc()
                # Ne pas break - continuer la boucle pour les prochains textes
                try:
                    self.speech_queue.task_done()
                except Exception:
                    pass
                continue

        print("[TTS Worker] Arrêt du worker TTS")
        self.is_speaking = False

    def _edge_tts_speak(self, text, voice=None):
        """Speak text using Microsoft Edge TTS (free, no API key needed).
        Runs asynchronously in a thread-safe manner."""
        # Utiliser la voix configurée, ou la voix par défaut
        if voice is None:
            voice = self.edge_voice if hasattr(self, 'edge_voice') and self.edge_voice else "fr-FR-HortenseNeural"
        
        async def _speak_async():
            try:
                edge_rate = f"{int(self.rate) - 100:+d}%"
                communicate = edge_tts.Communicate(text, voice, rate=edge_rate)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp_path = tmp.name
                await communicate.save(tmp_path)
                
                # Play the audio file
                if sys.platform == "win32":
                    # Use System.Windows.Media.MediaPlayer via PowerShell (supporte MP3, WAV, etc.)
                    # On détecte la durée du fichier via ffprobe ou on estime ~150 mots/min
                    try:
                        import json
                        probe = subprocess.run(
                            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", tmp_path],
                            capture_output=True, text=True, timeout=10
                        )
                        duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 5))
                    except Exception:
                        # Estimer la durée : ~2.5 secondes par mot court, +1s de marge
                        duration = max(3.0, len(text.split()) * 0.35 + 1.5)
                    
                    ps_script = f'''
                    Add-Type -AssemblyName presentationCore
                    $mplayer = New-Object System.Windows.Media.MediaPlayer
                    $mplayer.Open("{tmp_path}")
                    $mplayer.Play()
                    Start-Sleep -Seconds {duration + 0.5}
                    $mplayer.Stop()
                    $mplayer.Close()
                    '''
                    subprocess.run(
                        ["powershell", "-c", ps_script],
                        capture_output=True,
                        timeout=max(10, int(duration) + 5)
                    )
                else:
                    # Linux/macOS fallback
                    subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path],
                                   capture_output=True, timeout=60)
            except Exception as e:
                print(f"[Edge TTS] Error: {e}")
                # Fallback to pyttsx3 if edge-tts fails
                if pyttsx3 is not None:
                    print("[Edge TTS] Falling back to pyttsx3...")
                    self._pyttsx3_speak(text)
            finally:
                try:
                    if 'tmp_path' in locals():
                        os.unlink(tmp_path)
                except Exception:
                    pass
                
                # Trigger speech done callback
                if hasattr(self, 'on_speech_done') and self.on_speech_done:
                    try:
                        self.on_speech_done()
                    except Exception as e:
                        print(f"Error in on_speech_done callback: {e}")
        
        # Run async in a new event loop
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_speak_async())
            finally:
                loop.close()

        threading.Thread(target=run_async, daemon=True).start()

    def _pyttsx3_speak(self, text):
        """Speak text using pyttsx3 TTS engine (system voices)."""
        # Initialize COM for this thread on Windows
        if sys.platform == 'win32':
            import ctypes
            try:
                ctypes.windll.ole32.CoInitialize(None)
            except Exception:
                pass

        try:
            local_engine = pyttsx3.init()
            if self.voice_id:
                local_engine.setProperty('voice', self.voice_id)
            local_engine.setProperty('rate', self.rate)
            local_engine.setProperty('volume', self.volume)
            local_engine.say(text)
            local_engine.runAndWait()
        except Exception as e:
            print(f"[pyttsx3] Error speaking: {e}")

    def _pyttsx3_speak_inline(self, text):
        """Speak text using pyttsx3 inline (no files, no threading, in-memory only)."""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            # Si l'engine est cassé, en recréer un
            print(f"[pyttsx3] Engine error, reinitializing: {e}")
            try:
                self.engine = pyttsx3.init()
                if self.voice_id:
                    self.engine.setProperty('voice', self.voice_id)
                self.engine.setProperty('rate', self.rate)
                self.engine.setProperty('volume', self.volume)
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e2:
                print(f"[pyttsx3] Fatal error: {e2}")

    def speak(self, text):
        """Queue text to be spoken via the configured TTS provider."""
        if not text:
            return
        
        # Normalize text before speaking
        text = self._normalize_text(text)
        if not text:
            return
            
        print(f"[TTS] speak() appelé avec: '{text[:80]}...' - provider={self.tts_provider}")
        
        # Respecter le provider configuré dans config.json
        if self.tts_provider == "edge" and edge_tts is not None:
            print("[TTS] Utilisation Edge TTS (pas de blocage COM/thread)")
            self._edge_tts_speak(text)
            return
        
        if self.tts_provider == "pyttsx3" and pyttsx3 is not None:
            print("[TTS] Utilisation pyttsx3 (queue + worker thread)")
            # Réinitialiser le stop event si nécessaire
            if self.stop_speech_event.is_set():
                self.stop_speech_event.clear()
            
            # TOUJOURS vérifier que le worker est vivant
            if not self.tts_thread or not self.tts_thread.is_alive():
                print("[TTS] Worker thread mort ou absent, redémarrage...")
                self._start_tts_worker()
            
            self.speech_queue.put(text)
            return
        
        # Fallback : pyttsx3 dispo mais provider edge, ou edge non dispo
        if edge_tts is not None:
            print(f"[TTS] Fallback à Edge TTS (provider={self.tts_provider})")
            self._edge_tts_speak(text)
            return
        
        print(f"[TTS (Disabled)] Aucun provider TTS disponible: {text}")

    def stop_speaking(self):
        """Stop current speech and clear speech queue."""
        self.stop_speech_event.set()
        # Drain the queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except Exception:
                break
        
        if self.tts_thread:
            self.tts_thread.join(timeout=1.0)
        self.is_speaking = False

    def init_microphone(self):
        """Initializes the microphone. Returns True if successful, False otherwise."""
        if self.microphone is not None:
            return True
            
        try:
            # We list microphones to see if one is available
            mics = sr.Microphone.list_microphone_names()
            if not mics:
                print("No microphones found!")
                return False
            self.microphone = sr.Microphone()
            
            # Adjust for ambient noise once
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            return True
        except Exception as e:
            print(f"Error initializing microphone: {e}")
            return False

    def listen(self, timeout=5, phrase_time_limit=10):
        """Listens to microphone and returns transcribed text using Google Speech API."""
        if not self.init_microphone():
            return None, "Microphone non disponible"
            
        try:
            with self.microphone as source:
                print("[STT] listening...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                
            print("[STT] transcribing...")
            # Auto-detect language by trying multiple languages in order
            for lang in ["fr-FR", "en-US", "es-ES", "de-DE", "it-IT"]:
                try:
                    text = self.recognizer.recognize_google(audio, language=lang)
                    break
                except (sr.UnknownValueError, sr.RequestError):
                    continue
            else:
                return None, "Parole non comprise"
                    
            print(f"[STT] Transcribed: {text}")
            return text, None
        except sr.WaitTimeoutError:
            return None, "Délai d'attente dépassé (aucun son détecté)"
        except Exception as e:
            return None, f"Erreur de reconnaissance: {str(e)}"

    def _transcribe_audio(self, recognizer, audio):
        """Transcrit l'audio en testant plusieurs langues. Retourne le texte ou None."""
        text = ""
        for lang in ["fr-FR", "en-US", "es-ES", "de-DE", "it-IT"]:
            try:
                text = recognizer.recognize_google(audio, language=lang)
                return text.strip() if text else None
            except (sr.UnknownValueError, sr.RequestError):
                continue
        return None

    def _start_unified_listener(self):
        """Démarre un SEUL listener permanent qui route selon le mode (wake-word ou conversation).
        Plus besoin de stop/restart qui casse speech_recognition."""
        if self._listener_started:
            return
        if not self.init_microphone():
            print("[STT] Cannot start unified listener: no microphone.")
            return

        self._listener_started = True
        self.bg_listening_active = True
        print(f"[STT Unified] Listener permanent démarré. Wake word: '{self._wake_word}'")

        def unified_callback(recognizer, audio):
            try:
                text = self._transcribe_audio(recognizer, audio)
                if not text:
                    return

                text_lower = text.lower()
                print(f"[STT Unified] Heard: {text}")

                # --- MODE CONVERSATION : pas besoin de wake word ---
                if self.conversation_mode_active:
                    # Check for stop phrases
                    stop_phrases = ["stop", "arrête", "arrêtez", "termine", "fini",
                                    "c'est tout", "merci", "thanks", "thank you",
                                    "merci beaucoup", "au revoir", "bye", "rien",
                                    "c'est bon", "c'est tout bon"]
                    if any(phrase in text_lower for phrase in stop_phrases):
                        print("[Conversation Mode] Stop phrase detected, exiting.")
                        self.stop_conversation_mode()
                        return

                    # Reset timer
                    if hasattr(self, '_reset_conversation_timer'):
                        self._reset_conversation_timer(30)

                    # Submit text as user command
                    if hasattr(self, 'on_conversation_speech') and self.on_conversation_speech:
                        self.on_conversation_speech(text)
                    return

                # --- MODE WAKE WORD ---
                if self._wake_word and self._wake_word in text_lower:
                    print(f"[STT Unified] Wake word '{self._wake_word}' detected!")
                    
                    # ACTIVER LE MODE CONVERSATION IMMÉDIATEMENT
                    # Pour éviter la race condition : le listener doit être en mode
                    # conversation AVANT que la phrase suivante n'arrive
                    self.conversation_mode_active = True
                    self._reset_conversation_timer(30)
                    print(f"[STT Unified] Mode conversation activé (avant callback)")
                    
                    parts = text_lower.split(self._wake_word, 1)
                    command = parts[1].strip() if len(parts) > 1 else ""

                    if self._on_wake_callback:
                        self._on_wake_callback(command)

            except Exception as e:
                print(f"Error in unified callback: {e}")

        self.stop_background_listen_fn = self.recognizer.listen_in_background(
            self.microphone,
            unified_callback,
            phrase_time_limit=8
        )

    def start_background_listening(self, wake_word, on_wake_callback):
        """Configure le wake word et démarre le listener unifié (ou met à jour si déjà actif)."""
        self._wake_word = wake_word.lower()
        self._on_wake_callback = on_wake_callback
        self.bg_listening_active = True
        
        if not self._listener_started:
            self._start_unified_listener()
        else:
            print(f"[STT] Wake word mis à jour : '{self._wake_word}'")
            # Si on était en mode conversation, on le quitte pour revenir au wake word
            if self.conversation_mode_active:
                self.stop_conversation_mode()

    def start_conversation_mode(self, timeout_seconds=30, on_timeout=None):
        """Active le mode conversation sur le listener unifié existant.
        Le listener continue de tourner, il détecte juste les changements de mode."""
        # S'assurer que le listener unifié tourne
        if not self._listener_started:
            self._start_unified_listener()

        self.conversation_mode_active = True
        self.on_conversation_timeout = on_timeout

        # Démarrer le timer
        self._reset_conversation_timer(timeout_seconds)
        print(f"[Conversation Mode] Activé - écoute sans wake word pendant {timeout_seconds}s")

    def _reset_conversation_timer(self, timeout_seconds):
        """Reset or start the conversation inactivity timer."""
        if self.conversation_timer:
            self.conversation_timer.cancel()
        self.conversation_timer = threading.Timer(timeout_seconds, self._conversation_timeout)
        self.conversation_timer.daemon = True
        self.conversation_timer.start()

    def _conversation_timeout(self):
        """Called when conversation mode timer expires."""
        print("[Conversation Mode] Inactivity timeout - stopping conversation mode.")
        self.stop_conversation_mode()

    def stop_conversation_mode(self):
        """Désactive le mode conversation, retourne au mode wake-word.
        Le listener unifié continue de tourner, sans interruption."""
        self.conversation_mode_active = False

        if self.conversation_timer:
            self.conversation_timer.cancel()
            self.conversation_timer = None

        print("[Conversation Mode] Désactivé. Retour au mode wake-word.")

        # Call timeout callback (used by app.py)
        if self.on_conversation_timeout:
            cb = self.on_conversation_timeout
            self.on_conversation_timeout = None
            try:
                cb()
            except Exception as e:
                print(f"Error in conversation timeout callback: {e}")

    def stop_background_listening(self):
        """Arrête complètement le listener unifié."""
        if self.stop_background_listen_fn:
            self.stop_background_listen_fn(wait_for_stop=True)
            self.stop_background_listen_fn = None
        self.bg_listening_active = False
        self._listener_started = False
        self.conversation_mode_active = False
        print("[STT] Listener arrêté complètement.")
