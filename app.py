import os
import sys
import json
import time
import asyncio
import threading
import webbrowser
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

from voice import VoiceManager, EDGE_FRENCH_VOICES, EDGE_EXTRA_VOICES
from agent import Agent, load_config, save_config, translate_api_error
from personas import get_all_personas, get_persona, DEFAULT_PERSONA_ID
import tools

# Initialize FastAPI app
app = FastAPI(title="DeepSeek Agentic Voice Assistant")

# Content Security Policy Middleware to allow Websockets and inline scripts/evals on localhost
@app.middleware("http")
async def add_csp_header(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
        "script-src * 'unsafe-inline' 'unsafe-eval'; "
        "style-src * 'unsafe-inline'; "
        "connect-src * ws: wss:;"
    )
    return response

# Serve static files
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
        self.shutdown_timer = None
        self.has_connected = False

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.has_connected = True
        # Cancel shutdown timer if running
        if self.shutdown_timer:
            self.shutdown_timer.cancel()
            self.shutdown_timer = None
            print("[Système] Reconnexion détectée, annulation de l'arrêt.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # If no active connections left AND we have connected at least once, schedule system shutdown
        if not self.active_connections and self.has_connected:
            print("[Système] Plus de connexion WebSocket active. Fermeture de l'application programmée dans 15 secondes...")
            # Schedule delayed shutdown in the event loop
            try:
                self.shutdown_timer = asyncio.create_task(self.delayed_shutdown(15))
            except Exception as e:
                print(f"Error scheduling shutdown: {e}")

    async def delayed_shutdown(self, delay: int):
        await asyncio.sleep(delay)
        if not self.active_connections:
            print("[Système] Fermeture de l'application en cours...")
            await self.graceful_shutdown()

    async def graceful_shutdown(self):
        """Arrêt propre : notifie le frontend, nettoie les ressources, puis quitte."""
        print("[Système] Arrêt gracieux en cours...")
        # Notifier le frontend
        await self.broadcast({"type": "server_shutdown", "payload": {"message": "Le serveur s'arrête."}})
        await asyncio.sleep(0.5)
        # Cleanup voice
        if voice_manager:
            voice_manager.stop_background_listening()
            voice_manager.stop_speaking()
        # Sauvegarder l'historique si l'agent existe
        if agent and hasattr(agent, 'memory') and agent.memory:
            try:
                agent.memory.close()
            except Exception:
                pass
        print("[Système] Arrêt terminé.")
        # Fermeture propre du processus
        sys.exit(0)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be dead
                pass

manager = ConnectionManager()
main_loop = None

def broadcast_to_ui(message_type: str, payload: dict):
    """Safely broadcast a message to the UI from any thread."""
    if main_loop and manager.active_connections:
        coro = manager.broadcast({"type": message_type, "payload": payload})
        asyncio.run_coroutine_threadsafe(coro, main_loop)

# Global instances
voice_manager = None
agent = None

def on_speech_done_callback():
    """Triggered when pyttsx3 finishes speaking all queued text."""
    broadcast_to_ui("state_change", {"state": "IDLE"})
    
    # Réinitialiser le timer de conversation si le mode est actif
    # pour éviter que le timer n'expire pendant que l'assistant parlait
    if voice_manager and voice_manager.conversation_mode_active:
        voice_manager._reset_conversation_timer(30)

def agent_state_callback(state, data=None):
    """Triggered when agent state changes (THINKING, EXECUTING, SPEAKING, ERROR)."""
    broadcast_to_ui("state_change", {"state": state, "data": data})
    
    # If agent starts speaking, send text to voice manager
    if state == "SPEAKING" and data and "text" in data:
        text = data["text"]
        # Trigger TTS
        if voice_manager:
            voice_manager.speak(text)

def tool_log_callback(message):
    """Triggered when a desktop tool executes or logs activity."""
    broadcast_to_ui("tool_log", {"message": message})

# Register log listener in tools
tools.register_log_listener(tool_log_callback)

@app.get("/")
async def get_index():
    """Redirect to static index.html."""
    return RedirectResponse(url="/static/index.html")

# Thread worker functions
def run_agent_query(query):
    """Run agent query in a background thread to avoid blocking the event loop."""
    try:
        response = agent.run_query(query)
        broadcast_to_ui("chat_message", {"role": "assistant", "content": response})
    except Exception as e:
        err_str = str(e)
        # Traduire les erreurs techniques en messages utilisateur lisibles
        friendly_msg = translate_api_error(err_str)
        print(f"Error running agent query thread: {err_str}")
        broadcast_to_ui("toast", {"message": friendly_msg, "level": "error"})
        broadcast_to_ui("state_change", {"state": "ERROR", "data": {"message": friendly_msg}})

def run_manual_listen():
    """Run manual voice recognition in background thread."""
    if not voice_manager:
        return
        
    broadcast_to_ui("state_change", {"state": "LISTENING"})
    text, error = voice_manager.listen()
    
    if error:
        broadcast_to_ui("tool_log", {"message": f"[STT] {error}"})
        broadcast_to_ui("state_change", {"state": "IDLE"})
        if error != "Délai d'attente dépassé (aucun son détecté)" and error != "Parole non comprise":
            broadcast_to_ui("toast", {"message": error, "level": "error"})
    else:
        broadcast_to_ui("chat_message", {"role": "user", "content": text})
        # Start agent on transcribed text
        threading.Thread(target=run_agent_query, args=(text,), daemon=True).start()

def on_wake_word_detected(command):
    """Callback for background wake-word listener, launches conversation mode."""
    broadcast_to_ui("tool_log", {"message": f"[STT Background] Mot d'activation détecté ! Command: '{command}'"})
    
    # ACTIVER LE MODE CONVERSATION IMMÉDIATEMENT (avant le TTS qui est bloquant)
    # pour que l'utilisateur puisse parler pendant le "Oui ?"
    # Note: on_conversation_speech est déjà défini globalement dans main()
    if voice_manager and not voice_manager.conversation_mode_active:
        voice_manager.start_conversation_mode(
            timeout_seconds=30,
            on_timeout=None
        )
        broadcast_to_ui("state_change", {"state": "CONVERSATION_ACTIVE"})
        broadcast_to_ui("tool_log", {"message": "[Système] Mode conversation activé. Parlez maintenant..."})
    
    # Play acknowledgment dans un thread séparé (pour ne pas bloquer)
    def speak_ack():
        voice_manager.speak("Oui ?")
    threading.Thread(target=speak_ack, daemon=True).start()
    
    # If user directly said command (e.g., "Jarvis, ouvre Chrome")
    if command:
        broadcast_to_ui("chat_message", {"role": "user", "content": command})
        threading.Thread(target=run_agent_query, args=(command,), daemon=True).start()

def on_conversation_speech_detected(text):
    """Callback when speech is detected during conversation mode."""
    broadcast_to_ui("chat_message", {"role": "user", "content": text})
    threading.Thread(target=run_agent_query, args=(text,), daemon=True).start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global main_loop
    main_loop = asyncio.get_running_loop()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            payload = data.get("payload", {})
            
            if msg_type == "user_text_command":
                text = payload.get("text")
                if text:
                    # Run agent query in background thread
                    threading.Thread(target=run_agent_query, args=(text,), daemon=True).start()
                    
            elif msg_type == "start_listening":
                # Cancel current speech if any
                voice_manager.stop_speaking()
                # Run speech recognition in background thread
                threading.Thread(target=run_manual_listen, daemon=True).start()
                
            elif msg_type == "stop_listening":
                # Standard voice listening doesn't easily cancel, but we reset UI state
                broadcast_to_ui("state_change", {"state": "IDLE"})
                
            elif msg_type == "trigger_ocr_scan":
                # Run OCR in background and log to console
                def run_ocr():
                    res = tools.take_screenshot_and_ocr()
                    if "error" in res:
                        broadcast_to_ui("tool_log", {"message": f"[OCR] Échec : {res['error']}"})
                    else:
                        text_sample = res.get("raw_text", "")
                        # Shorten for log display
                        sample = (text_sample[:100] + '...') if len(text_sample) > 100 else text_sample
                        broadcast_to_ui("tool_log", {"message": f"[OCR] Réussi. Texte trouvé : {sample}"})
                        
                threading.Thread(target=run_ocr, daemon=True).start()
                
            elif msg_type == "emergency_stop":
                agent.abort()
                voice_manager.stop_speaking()
                broadcast_to_ui("tool_log", {"message": "[Système] Actions et voix interrompues par l'utilisateur."})
                broadcast_to_ui("state_change", {"state": "IDLE"})
                
            elif msg_type == "get_settings":
                config = load_config()
                # Remove sensitive api key before sending, or obfuscate it
                api_key = config.get("api_key", "")
                obfuscated_key = api_key[:6] + "*" * (len(api_key) - 10) + api_key[-4:] if len(api_key) > 10 else api_key
                config_to_send = config.copy()
                config_to_send["api_key"] = ""  # SECURITY FIX: Never send actual API key to frontend
                config_to_send["api_key_obfuscated"] = obfuscated_key  # Send obfuscated for display only
                config_to_send["continuous_listening"] = voice_manager.bg_listening_active
                await websocket.send_json({"type": "settings_data", "payload": config_to_send})
                
            elif msg_type == "save_settings":
                # Save configuration
                api_key = payload.get("api_key", "")
                tts_rate = payload.get("tts_rate", 120) or 120
                # If obfuscated was returned, don't overwrite if it wasn't modified
                # But here the UI sends the actual value. We just save.
                config_data = {
                    "api_key": api_key,
                    "base_url": payload.get("base_url"),
                    "model": payload.get("model"),
                    "wake_word": payload.get("wake_word"),
                    "tts_provider": payload.get("tts_provider", "edge"),
                    "tts_voice_id": payload.get("tts_voice_id", ""),
                    "tts_edge_voice": payload.get("tts_edge_voice", "fr-FR-HortenseNeural"),
                    "tts_rate": tts_rate,
                    "tts_volume": payload.get("tts_volume"),
                    "persona_id": payload.get("persona_id", "jarvis")
                }
                save_config(config_data)
                
                # Apply TTS updates
                voice_manager.set_voice(payload.get("tts_voice_id"))
                voice_manager.set_rate(tts_rate)
                voice_manager.volume = payload.get("tts_volume")
                # Appliquer la voix Edge TTS sélectionnée
                voice_manager.edge_voice = payload.get("tts_edge_voice", "fr-FR-HortenseNeural")
                voice_manager.tts_provider = payload.get("tts_provider", "edge")
                
                # Appliquer la personnalité IA sélectionnée
                persona_id = payload.get("persona_id", "jarvis")
                if agent:
                    agent.persona_id = persona_id
                    # Mettre à jour aussi la voix recommandée si l'utilisateur n'a pas changé la voix manuellement
                    persona = get_persona(persona_id)
                    if persona and payload.get("auto_set_voice", True):
                        # Proposer la voix recommandée pour cette personnalité
                        pass  # La voix est déjà gérée par le sélecteur TTS
                
                # Toggle / Restart continuous listen to apply new wake word
                continuous = payload.get("continuous_listening", False)
                if voice_manager.bg_listening_active:
                    voice_manager.stop_background_listening()
                
                if continuous:
                    voice_manager.start_background_listening(payload.get("wake_word", "ordinateur"), on_wake_detected_wrapper)
                    
                await websocket.send_json({"type": "toast", "payload": {"message": "Paramètres appliqués", "level": "success"}})
                
            elif msg_type == "get_voices":
                # Récupérer les voix SAPI5 système
                sapi5_voices = voice_manager.get_voices()
                # Récupérer les voix Edge TTS depuis voice.py
                edge_voices = EDGE_FRENCH_VOICES + EDGE_EXTRA_VOICES
                config = load_config()
                selected_sapi5 = config.get("tts_voice_id", "")
                selected_edge = config.get("tts_edge_voice", "fr-FR-HortenseNeural")
                tts_provider = config.get("tts_provider", "edge")
                await websocket.send_json({
                    "type": "voices_list", 
                    "payload": {
                        "sapi5_voices": sapi5_voices,
                        "edge_voices": edge_voices,
                        "selected_sapi5_voice": selected_sapi5,
                        "selected_edge_voice": selected_edge,
                        "tts_provider": tts_provider
                    }
                })
                
            elif msg_type == "toggle_continuous_listening":
                active = payload.get("active", False)
                config = load_config()
                wake_word = config.get("wake_word", "ordinateur")
                if active:
                    voice_manager.start_background_listening(wake_word, on_wake_detected_wrapper)
                else:
                    voice_manager.stop_background_listening()
                broadcast_to_ui("tool_log", {"message": f"[Système] Écoute continue : {'Activée' if active else 'Désactivée'}"})
                
            elif msg_type == "get_personas":
                # Envoyer la liste des personnalités disponibles
                all_personas = get_all_personas()
                config = load_config()
                current_persona_id = config.get("persona_id", DEFAULT_PERSONA_ID)
                await websocket.send_json({
                    "type": "personas_list",
                    "payload": {
                        "personas": all_personas,
                        "current_persona_id": current_persona_id,
                        "default_persona_id": DEFAULT_PERSONA_ID
                    }
                })
                
            elif msg_type == "clear_history":
                agent.conversation_history = []
                broadcast_to_ui("tool_log", {"message": "[Système] Historique des conversations réinitialisé."})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

def on_wake_detected_wrapper(command):
    """Wrapper to handle thread safe wake word callback."""
    # We call our local callback in a separate thread so it doesn't block the listener
    threading.Thread(target=on_wake_word_detected, args=(command,), daemon=True).start()

def main():
    global main_loop, voice_manager, agent
    
    print("Initialisation des modules de l'assistant...")
    
    # Load configuration
    config = load_config()
    
    # Initialize Voice Manager
    voice_manager = VoiceManager(
        voice_id=config.get("tts_voice_id"),
        rate=config.get("tts_rate", 120),
        volume=config.get("tts_volume", 1.0),
        tts_provider=config.get("tts_provider", "pyttsx3"),
        edge_voice=config.get("tts_edge_voice", "fr-FR-HortenseNeural")
    )
    voice_manager.on_speech_done = on_speech_done_callback
    voice_manager.on_conversation_speech = on_conversation_speech_detected  # Défini une fois pour toutes
    
    # Enregistrer le voice_manager pour les outils TTS (switch_tts_voice, get_available_voices)
    tools.set_voice_manager(voice_manager)
    
    # Initialize Agent
    agent = Agent(state_callback=agent_state_callback)
    
    # Try starting background continuous listening if active in settings
    # We don't have it enabled by default, user can toggle it on UI
    
    # Automatically open local page in browser after server starts
    def open_browser():
        time.sleep(1.5)
        print("Ouverture du navigateur sur le tableau de bord...")
        webbrowser.open("http://localhost:8000")
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start web server
    print("Démarrage du serveur web FastAPI sur http://localhost:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    main()
