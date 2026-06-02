import os
import sys
import json
import time
import tempfile
import subprocess
import webbrowser
import shutil
import urllib.request
import threading
import zipfile
import pyautogui
from PIL import ImageGrab

# PyAutoGUI safety configuration
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.5       # Add half second pause after each call to allow user to take back control

_log_listeners = []

# Référence au VoiceManager (définie par app.py)
_voice_manager = None

def set_voice_manager(vm):
    """Enregistre l'instance VoiceManager pour permettre aux outils de changer la voix."""
    global _voice_manager
    _voice_manager = vm

def register_log_listener(listener):
    """Register a callback for tool activity logging."""
    if listener not in _log_listeners:
        _log_listeners.append(listener)

def log_action(message):
    """Log an action and notify all registered listeners."""
    print(f"[Tool] {message}")
    for listener in _log_listeners:
        try:
            listener(message)
        except Exception as e:
            print(f"Error in tool log listener: {e}")

def get_screen_resolution():
    """Returns screen width and height as a dict."""
    try:
        width, height = pyautogui.size()
        log_action(f"Résolution de l'écran récupérée : {width}x{height}")
        return {"width": width, "height": height}
    except Exception as e:
        log_action(f"Erreur lors de la récupération de la résolution : {e}")
        return {"error": str(e)}

def take_screenshot_and_ocr():
    """Captures screen, runs local Windows OCR via ocr.ps1, and returns structured text elements."""
    log_action("Capture d'écran et analyse OCR locale en cours...")
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"ocr_capture_{int(time.time())}.png")
    
    try:
        # Capture screenshot
        screenshot = ImageGrab.grab()
        screenshot.save(temp_path, "PNG")
        
        # Determine script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ps_script_path = os.path.join(script_dir, "ocr.ps1")
        
        if not os.path.exists(ps_script_path):
            return {"error": f"Script OCR non trouvé à l'emplacement : {ps_script_path}"}
            
        # Run PowerShell OCR script
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-File", ps_script_path,
            "-ImagePath", temp_path
        ]
        
        # Run command hidden
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            startupinfo=startupinfo,
            encoding='utf-8', 
            errors='ignore'
        )
        
        # Clean up temporary screenshot
        try:
            os.remove(temp_path)
        except Exception:
            pass
            
        # Sanitize the PowerShell output before parsing
        raw_output = result.stdout
        # Strip BOM and leading/trailing whitespace
        raw_output = raw_output.strip().lstrip('\ufeff')
        # Remove control characters (except normal whitespace) that break JSON
        import re
        raw_output = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw_output)
        
        try:
            ocr_data = json.loads(raw_output, strict=False)
        except json.JSONDecodeError as je:
            log_action(f"Erreur de parsing JSON OCR: {je}")
            # Fallback: try to extract just the text field via regex
            text_match = re.search(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_output)
            if text_match:
                fallback_text = text_match.group(1)
                log_action(f"OCR Fallback : texte brut extrait ({len(fallback_text)} chars)")
                return {"raw_text": fallback_text, "elements": []}
            return {"error": f"Impossible de parser le JSON de l'OCR: {str(je)}"}
        
        if not ocr_data.get("success", False):
            log_action(f"Échec de l'OCR : {ocr_data.get('error', 'Erreur inconnue')}")
            return {"error": ocr_data.get("error", "Erreur OCR inconnue")}
            
        raw_text = ocr_data.get("text", "")
        lines = ocr_data.get("lines", [])
        
        # Format a highly-readable version of the elements for the LLM
        formatted_elements = []
        log_action(f"OCR terminé. {len(lines)} lignes de texte détectées.")
        
        for line in lines:
            line_text = line.get("text", "")
            words = line.get("words", [])
            if not words:
                continue
                
            # Calculate full line bounding rect by combining words
            x_coords = [w.get("x", 0) for w in words]
            y_coords = [w.get("y", 0) for w in words]
            widths = [w.get("width", 0) for w in words]
            heights = [w.get("height", 0) for w in words]
            
            min_x = min(x_coords)
            min_y = min(y_coords)
            max_x = max([x + w for x, w in zip(x_coords, widths)])
            max_y = max([y + h for y, h in zip(y_coords, heights)])
            
            width = max_x - min_x
            height = max_y - min_y
            center_x = min_x + (width // 2)
            center_y = min_y + (height // 2)
            
            formatted_elements.append({
                "text": line_text,
                "x": center_x,
                "y": center_y,
                "bbox": [min_x, min_y, width, height]
            })
            
        return {
            "raw_text": raw_text,
            "elements": formatted_elements
        }
        
    except Exception as e:
        log_action(f"Erreur lors de la capture/OCR : {e}")
        return {"error": str(e)}

def mouse_click(x, y, button="left", double_click=False):
    """Clicks the mouse at coordinate (x, y)."""
    try:
        x, y = int(x), int(y)
        action_name = "Double-clic" if double_click else "Clic"
        log_action(f"{action_name} {button} à la position ({x}, {y})")
        
        pyautogui.moveTo(x, y, duration=0.3)
        if double_click:
            pyautogui.doubleClick(button=button)
        else:
            pyautogui.click(button=button)
        return {"status": "success", "action": "click", "x": x, "y": y}
    except Exception as e:
        log_action(f"Erreur lors du clic à ({x}, {y}) : {e}")
        return {"error": str(e)}

def mouse_move(x, y):
    """Moves the mouse cursor to (x, y)."""
    try:
        x, y = int(x), int(y)
        log_action(f"Déplacement de la souris à ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.5)
        return {"status": "success", "action": "move", "x": x, "y": y}
    except Exception as e:
        log_action(f"Erreur déplacement souris : {e}")
        return {"error": str(e)}

def mouse_drag(x, y):
    """Drags mouse to (x, y) holding left button."""
    try:
        x, y = int(x), int(y)
        log_action(f"Glisser la souris vers ({x}, {y})")
        pyautogui.dragTo(x, y, duration=0.5, button='left')
        return {"status": "success", "action": "drag", "x": x, "y": y}
    except Exception as e:
        log_action(f"Erreur glisser souris : {e}")
        return {"error": str(e)}

def mouse_scroll(direction="down", clicks=3):
    """Scrolls mouse wheel. direction can be 'up' or 'down'."""
    try:
        clicks = int(clicks)
        amount = -clicks if direction == "down" else clicks
        # On Windows, positive scrolls up, negative scrolls down.
        # Pyroautogui scroll receives an integer.
        log_action(f"Défilement (scroll) {direction} de {clicks} clics")
        pyautogui.scroll(amount * 100) # multiplier for larger scroll on windows
        return {"status": "success", "action": "scroll", "direction": direction, "clicks": clicks}
    except Exception as e:
        log_action(f"Erreur scroll : {e}")
        return {"error": str(e)}

def keyboard_type(text):
    """Types text on keyboard."""
    try:
        # Avoid logging sensitive texts but log length
        log_action(f"Saisie du texte (Longueur : {len(text)})")
        pyautogui.write(text, interval=0.01)
        return {"status": "success", "action": "type", "length": len(text)}
    except Exception as e:
        log_action(f"Erreur saisie clavier : {e}")
        return {"error": str(e)}

def keyboard_press(key):
    """Presses a key or key combination (hotkey). E.g. 'enter', 'win', 'ctrl+c', 'alt+f4'."""
    try:
        log_action(f"Pression clavier : '{key}'")
        if '+' in key:
            keys = [k.strip() for k in key.split('+')]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)
        return {"status": "success", "action": "press", "key": key}
    except Exception as e:
        log_action(f"Erreur touche clavier : {e}")
        return {"error": str(e)}

def execute_system_command(command):
    """Executes a system command in PowerShell and returns output."""
    log_action(f"Exécution de la commande système : {command}")
    try:
        # Run command hidden
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(
            ["powershell.exe", "-Command", command],
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            encoding='utf-8',
            errors='ignore',
            timeout=30 # 30s timeout
        )
        
        status = "success" if result.returncode == 0 else "failed"
        log_action(f"Commande terminée avec le code de sortie {result.returncode}")
        
        return {
            "status": status,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        log_action("Commande système expirée (timeout de 30 secondes).")
        return {"status": "timeout", "error": "Le délai d'exécution de 30 secondes a expiré."}
    except Exception as e:
        log_action(f"Erreur d'exécution de la commande : {e}")
        return {"status": "error", "error": str(e)}

def file_action(action, path, content=None):
    """Performs file system actions. action: 'read', 'write', 'append', 'delete', 'list'."""
    try:
        path = os.path.abspath(path)
        log_action(f"Action fichier '{action}' sur : {path}")
        
        if action == 'read':
            if not os.path.exists(path):
                return {"error": "Fichier non trouvé"}
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return {"status": "success", "content": f.read()}
                
        elif action == 'write':
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content or "")
            return {"status": "success", "message": "Fichier écrit avec succès"}
            
        elif action == 'append':
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content or "")
            return {"status": "success", "message": "Fichier modifié (append) avec succès"}
            
        elif action == 'delete':
            if not os.path.exists(path):
                return {"error": "Fichier non trouvé"}
            if os.path.isdir(path):
                os.rmdir(path) # removes empty directory
            else:
                os.remove(path)
            return {"status": "success", "message": "Élément supprimé avec succès"}
            
        elif action == 'list':
            if not os.path.exists(path):
                return {"error": "Répertoire non trouvé"}
            if not os.path.isdir(path):
                return {"error": "Le chemin spécifié n'est pas un dossier"}
            items = os.listdir(path)
            details = []
            for item in items:
                item_path = os.path.join(path, item)
                details.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                })
            return {"status": "success", "items": details}
            
        else:
            return {"error": f"Action inconnue : {action}"}
            
    except Exception as e:
        log_action(f"Erreur opération fichier : {e}")
        return {"error": str(e)}

def wait(seconds):
    """Waits for specified amount of seconds."""
    try:
        seconds = float(seconds)
        log_action(f"Pause de {seconds} secondes...")
        time.sleep(seconds)
        return {"status": "success", "message": f"Attente de {seconds} secondes terminée."}
    except Exception as e:
        log_action(f"Erreur wait : {e}")
        return {"error": str(e)}

def open_url(url):
    """Ouvre un site web dans le navigateur par défaut."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        log_action(f"Ouverture de l'URL : {url}")
        webbrowser.open(url)
        return {"success": True, "url": url}
    except Exception as e:
        log_action(f"Erreur open_url : {e}")
        return {"error": str(e)}

def get_clipboard():
    """Lit le contenu du presse-papier Windows."""
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=5
        )
        text = result.stdout.strip()
        log_action(f"Presse-papier lu ({len(text)} caractères)")
        return {"text": text}
    except subprocess.TimeoutExpired:
        return {"error": "Timeout lors de la lecture du presse-papier"}
    except Exception as e:
        log_action(f"Erreur get_clipboard : {e}")
        return {"error": str(e)}

def set_clipboard(text):
    """Écrit du texte dans le presse-papier Windows."""
    try:
        # Escape single quotes for PowerShell
        safe_text = text.replace("'", "''")
        subprocess.run(
            ["powershell.exe", "-Command", f"Set-Clipboard -Value '{safe_text}'"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )
        log_action(f"Texte copié dans le presse-papier ({len(text)} caractères)")
        return {"success": True}
    except Exception as e:
        log_action(f"Erreur set_clipboard : {e}")
        return {"error": str(e)}

def get_active_window():
    """Récupère le titre et le processus de la fenêtre active."""
    try:
        ps_script = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinAPI {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@
$hwnd = [WinAPI]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder(256)
[WinAPI]::GetWindowText($hwnd, $sb, 256) | Out-Null
$pid = 0
[WinAPI]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
$process = (Get-Process -Id $pid).ProcessName
@{title=$sb.ToString(); process=$process; pid=$pid} | ConvertTo-Json
'''
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )
        data = json.loads(result.stdout.strip())
        log_action(f"Fenêtre active : {data.get('title', '')} ({data.get('process', '')})")
        return {"title": data.get("title", ""), "process": data.get("process", ""), "pid": data.get("pid", 0)}
    except subprocess.TimeoutExpired:
        return {"error": "Timeout lors de la récupération de la fenêtre active"}
    except Exception as e:
        log_action(f"Erreur get_active_window : {e}")
        return {"error": str(e)}

def get_system_info():
    """Récupère les informations système (CPU, RAM, disque, réseau)."""
    try:
        import psutil
        import socket
        
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        
        info = {
            "hostname": hostname,
            "ip": ip,
            "cpu_percent": cpu,
            "cpu_cores": psutil.cpu_count(logical=True),
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "ram_used_gb": round(mem.used / (1024**3), 1),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "disk_percent": disk.percent
        }
        log_action(f"Infos système : CPU {cpu}%, RAM {mem.percent}%, Disque {disk.percent}%")
        return info
    except ImportError:
        return {"error": "Module 'psutil' non installé. Exécutez 'pip install psutil'."}
    except Exception as e:
        log_action(f"Erreur get_system_info : {e}")
        return {"error": str(e)}

# ============================================================================
# NOUVEAUX OUTILS — Amélioration n°8
# ============================================================================

def system_volume_control(action="get", level=None):
    """Contrôle le volume système Windows (lecture ou modification).
    action: 'get' pour lire, 'set' pour modifier, 'mute' pour couper/activer.
    level: niveau entre 0 et 100 (pour 'set')."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        
        if action == "get":
            current = int(round(volume.GetMasterVolumeLevelScalar() * 100))
            muted = volume.GetMute()
            log_action(f"Volume système : {current}% (muet: {muted})")
            return {"volume": current, "muted": muted}
        elif action == "set" and level is not None:
            level = max(0, min(100, int(level)))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            log_action(f"Volume système réglé à {level}%")
            return {"success": True, "volume": level}
        elif action == "mute":
            current_mute = volume.GetMute()
            volume.SetMute(not current_mute, None)
            new_state = "coupé" if not current_mute else "rétabli"
            log_action(f"Son {new_state}")
            return {"success": True, "muted": not current_mute}
        else:
            return {"error": f"Action volume inconnue : {action}"}
    except ImportError:
        return {"error": "Modules 'pycaw' et 'comtypes' non installés. pip install pycaw comtypes"}
    except Exception as e:
        log_action(f"Erreur volume : {e}")
        return {"error": str(e)}


def read_document(filepath):
    """Lit le contenu d'un fichier PDF ou DOCX et retourne le texte extrait."""
    if not os.path.exists(filepath):
        return {"error": f"Fichier non trouvé : {filepath}"}
    
    ext = os.path.splitext(filepath)[1].lower()
    log_action(f"Lecture du document : {filepath}")
    
    try:
        if ext == ".pdf":
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(filepath)
                text_parts = []
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                full_text = "\n\n".join(text_parts)
                log_action(f"PDF lu : {len(reader.pages)} pages, {len(full_text)} caractères")
                return {"success": True, "format": "pdf", "pages": len(reader.pages), "text": full_text}
            except ImportError:
                return {"error": "Module 'PyPDF2' non installé. pip install PyPDF2"}
                
        elif ext == ".docx":
            try:
                from docx import Document
                doc = Document(filepath)
                text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
                full_text = "\n".join(text_parts)
                log_action(f"DOCX lu : {len(text_parts)} paragraphes, {len(full_text)} caractères")
                return {"success": True, "format": "docx", "paragraphs": len(text_parts), "text": full_text}
            except ImportError:
                return {"error": "Module 'python-docx' non installé. pip install python-docx"}
                
        elif ext == ".txt":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            log_action(f"TXT lu : {len(text)} caractères")
            return {"success": True, "format": "txt", "text": text}
            
        else:
            return {"error": f"Format non supporté : {ext}. Formats acceptés : .pdf, .docx, .txt"}
            
    except Exception as e:
        log_action(f"Erreur lecture document : {e}")
        return {"error": str(e)}


def get_weather(city):
    """Récupère la météo actuelle d'une ville via wttr.in (API gratuite, pas de clé)."""
    try:
        import urllib.request
        import urllib.parse
        
        encoded_city = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded_city}?format=j1&lang=fr"
        
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        current = data.get("current_condition", [{}])[0]
        weather_info = {
            "city": city,
            "temperature_c": current.get("temp_C", "N/A"),
            "humidite": current.get("humidity", "N/A"),
            "vent_kmh": current.get("windspeedKmph", "N/A"),
            "description": current.get("weatherDesc", [{"value": "N/A"}])[0]["value"],
            "ressenti_c": current.get("FeelsLikeC", "N/A"),
            "visibilite_km": current.get("visibility", "N/A")
        }
        log_action(f"Météo pour {city} : {weather_info['temperature_c']}°C, {weather_info['description']}")
        return weather_info
    except ImportError:
        return {"error": "Modules manquants"}
    except Exception as e:
        log_action(f"Erreur météo pour {city} : {e}")
        return {"error": f"Impossible de récupérer la météo pour '{city}'. Vérifiez le nom de la ville."}


def get_news(query=None, limit=5):
    """Récupère les titres d'actualités via DuckDuckGo News (sans clé API).
    query: terme de recherche (optionnel, sinon actualités générales)."""
    try:
        from duckduckgo_search import DDGS
        
        search_query = query if query else "actualités France"
        log_action(f"Recherche d'actualités : '{search_query}'")
        
        with DDGS() as ddgs:
            results = list(ddgs.news(search_query, region="fr-fr", max_results=limit))
        
        articles = []
        for r in results:
            articles.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "source": r.get("source", ""),
                "date": r.get("date", ""),
                "snippet": r.get("body", "")[:200]
            })
        
        log_action(f"{len(articles)} actualités trouvées pour '{search_query}'")
        return {"query": search_query, "count": len(articles), "articles": articles}
    except ImportError:
        return {"error": "Module 'duckduckgo-search' non installé. pip install duckduckgo-search"}
    except Exception as e:
        log_action(f"Erreur actualités : {e}")
        return {"error": str(e)}


def send_notification(title, message):
    """Envoie une notification Windows native (popup système)."""
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=5, threaded=True)
        log_action(f"Notification envoyée : '{title}'")
        return {"success": True, "title": title}
    except ImportError:
        # Fallback PowerShell
        try:
            ps_cmd = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Assistant").Show($toast)
            '''
            subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                         capture_output=True, timeout=10)
            log_action(f"Notification PowerShell envoyée : '{title}'")
            return {"success": True, "title": title}
        except Exception as e2:
            log_action(f"Erreur notification : {e2}")
            return {"error": f"Notification impossible : {e2}"}


def web_search(query, limit=5):
    """Effectue une recherche web via DuckDuckGo et retourne les résultats (sans clé API)."""
    try:
        from duckduckgo_search import DDGS
        
        log_action(f"Recherche web : '{query}'")
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="fr-fr", max_results=limit))
        
        items = []
        for r in results:
            items.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")[:300]
            })
        
        log_action(f"{len(items)} résultats web pour '{query}'")
        return {"query": query, "count": len(items), "results": items}
    except ImportError:
        return {"error": "Module 'duckduckgo-search' non installé. pip install duckduckgo-search"}
    except Exception as e:
        log_action(f"Erreur recherche web : {e}")
        return {"error": str(e)}


# ============================================================================
# NOUVEAUX OUTILS (v2) — download_file, get_cursor_position, extract_archive,
# set_reminder, list_processes, kill_process, get_battery_status, play_youtube, text_to_file
# ============================================================================

def download_file(url, filename=None):
    """
    Télécharge un fichier depuis une URL vers le dossier Téléchargements.
    Retourne le chemin complet du fichier téléchargé.
    """
    try:
        # Déterminer le dossier de destination (Téléchargements)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads):
            downloads = os.path.join(os.path.expanduser("~"), "Téléchargements")
        if not os.path.exists(downloads):
            os.makedirs(downloads, exist_ok=True)
        
        # Extraire le nom du fichier depuis l'URL si pas fourni
        if not filename:
            filename = url.split("/")[-1].split("?")[0]
            if not filename or "." not in filename:
                filename = f"download_{int(time.time())}"
        
        dest_path = os.path.join(downloads, filename)
        
        log_action(f"Téléchargement de {url} → {dest_path}")
        
        urllib.request.urlretrieve(url, dest_path)
        file_size = os.path.getsize(dest_path)
        
        log_action(f"Téléchargement terminé : {filename} ({file_size} octets)")
        return {
            "success": True,
            "path": dest_path,
            "filename": filename,
            "size_bytes": file_size,
            "size_readable": f"{file_size / 1024:.1f} Ko" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} Mo"
        }
    except Exception as e:
        log_action(f"Erreur téléchargement : {e}")
        return {"error": f"Échec du téléchargement : {str(e)}"}


def get_cursor_position():
    """
    Retourne la position actuelle (x, y) du curseur de la souris.
    Utile pour le debugging et les scripts de positionnement.
    """
    try:
        x, y = pyautogui.position()
        log_action(f"Position du curseur : ({x}, {y})")
        return {"x": x, "y": y}
    except Exception as e:
        log_action(f"Erreur position curseur : {e}")
        return {"error": str(e)}


def extract_archive(archive_path, dest_folder=None):
    """
    Décompresse une archive (ZIP, RAR, 7z) dans un dossier de destination.
    Supporte ZIP (natif) et RAR/7z via 7z.exe si installé.
    """
    try:
        if not os.path.exists(archive_path):
            return {"error": f"Archive non trouvée : {archive_path}"}
        
        # Dossier de destination par défaut : même dossier que l'archive + _extracted
        if not dest_folder:
            base = os.path.splitext(archive_path)[0]
            dest_folder = f"{base}_extracted"
        
        os.makedirs(dest_folder, exist_ok=True)
        
        ext = os.path.splitext(archive_path)[1].lower()
        log_action(f"Extraction de {archive_path} → {dest_folder}")
        
        if ext == ".zip":
            with zipfile.ZipFile(archive_path, 'r') as z:
                z.extractall(dest_folder)
                file_count = len(z.namelist())
            log_action(f"ZIP extrait : {file_count} fichiers dans {dest_folder}")
            return {"success": True, "format": "zip", "files_extracted": file_count, "dest_folder": dest_folder}
        
        elif ext in [".rar", ".7z"]:
            # Essayer 7z.exe (installé ou portable)
            seven_zip_paths = [
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "7z.exe")
            ]
            seven_zip = None
            for p in seven_zip_paths:
                if os.path.exists(p):
                    seven_zip = p
                    break
            
            if not seven_zip:
                return {"error": f"Format {ext} nécessite 7-Zip. Installez 7-Zip ou utilisez une archive ZIP."}
            
            result = subprocess.run(
                [seven_zip, "x", archive_path, f"-o{dest_folder}", "-y"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                files = [f for f in os.listdir(dest_folder)]
                log_action(f"Archive {ext} extraite : {len(files)} éléments dans {dest_folder}")
                return {"success": True, "format": ext, "elements_count": len(files), "dest_folder": dest_folder}
            else:
                return {"error": f"Erreur 7z : {result.stderr or result.stdout}"}
        
        else:
            return {"error": f"Format non supporté : {ext}. Utilisez .zip, .rar ou .7z"}
    
    except Exception as e:
        log_action(f"Erreur extraction : {e}")
        return {"error": str(e)}


def set_reminder(message, delay_seconds=60):
    """
    Programme un rappel qui déclenche une notification Windows + lecture vocale (TTS)
    après le délai spécifié en secondes.
    Exemples : 'Rappelle-moi dans 5 minutes de sortir le poulet' → delay_seconds=300
    """
    try:
        delay_seconds = int(delay_seconds)
        log_action(f"Rappel programmé dans {delay_seconds}s : '{message}'")
        
        def _trigger_reminder():
            try:
                time.sleep(delay_seconds)
                # Notification Windows
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast("⏰ Rappel", message, duration=10, threaded=True)
                except Exception:
                    # Fallback PowerShell
                    ps_cmd = f'''
                    Add-Type -AssemblyName System.Windows.Forms
                    $notify = New-Object System.Windows.Forms.NotifyIcon
                    $notify.Icon = [System.Drawing.SystemIcons]::Information
                    $notify.BalloonTipTitle = "Rappel"
                    $notify.BalloonTipText = "{message}"
                    $notify.Visible = $true
                    $notify.ShowBalloonTip(10000)
                    Start-Sleep -Seconds 10
                    $notify.Dispose()
                    '''
                    subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                                 capture_output=True, timeout=20)
                
                # TTS vocal
                if _voice_manager:
                    _voice_manager.speak(f"Rappel : {message}")
                
                log_action(f"Rappel déclenché : '{message}'")
            except Exception as e:
                print(f"[Reminder] Erreur déclenchement rappel : {e}")
        
        t = threading.Thread(target=_trigger_reminder, daemon=True)
        t.start()
        
        mins = delay_seconds // 60
        secs = delay_seconds % 60
        human_delay = f"{mins} min {secs}s" if mins > 0 else f"{secs} secondes"
        
        return {
            "success": True,
            "message": message,
            "delay_seconds": delay_seconds,
            "delay_human": human_delay
        }
    except Exception as e:
        log_action(f"Erreur rappel : {e}")
        return {"error": str(e)}


def list_processes(filter_name=None, top=20):
    """
    Liste les processus Windows en cours d'exécution avec leur nom, PID, CPU et mémoire.
    filter_name : filtre optionnel par nom (ex: 'chrome', 'python').
    top : nombre maximum de processus à retourner (défaut 20).
    """
    try:
        ps_script = f'''
        Get-Process {"-Name '*" + filter_name + "*'" if filter_name else ""} | 
            Sort-Object -Property CPU -Descending | 
            Select-Object -First {top} |
            ForEach-Object {{
                @{{
                    name = $_.ProcessName
                    pid = $_.Id
                    cpu_s = [math]::Round($_.CPU, 1)
                    memory_mb = [math]::Round($_.WorkingSet64 / 1MB, 1)
                    threads = $_.Threads.Count
                    responding = $_.Responding
                }}
            }} | ConvertTo-Json -Compress
        '''
        
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=15
        )
        
        if not result.stdout.strip():
            return {"processes": [], "count": 0, "filter": filter_name}
        
        try:
            processes = json.loads(result.stdout.strip())
            if isinstance(processes, dict):
                processes = [processes]
            
            log_action(f"{len(processes)} processus listés" + (f" (filtre: {filter_name})" if filter_name else ""))
            return {
                "processes": processes,
                "count": len(processes),
                "filter": filter_name,
                "top": top
            }
        except json.JSONDecodeError:
            return {"error": f"Impossible de parser la sortie PowerShell", "raw": result.stdout[:500]}
    
    except subprocess.TimeoutExpired:
        return {"error": "Timeout lors du listage des processus"}
    except Exception as e:
        log_action(f"Erreur list_processes : {e}")
        return {"error": str(e)}


def kill_process(name=None, pid=None):
    """
    Ferme (tue) un processus Windows par son nom ou son PID.
    name : nom du processus (ex: 'notepad', 'chrome').
    pid : ID numérique du processus.
    """
    try:
        if name:
            log_action(f"Fermeture du processus : {name}")
            result = subprocess.run(
                ["taskkill", "/F", "/IM", name],
                capture_output=True, text=True, timeout=15
            )
            if "SUCCESS" in result.stdout or result.returncode == 0:
                log_action(f"Processus '{name}' fermé avec succès")
                return {"success": True, "target": name, "method": "name"}
            else:
                return {"error": f"Impossible de fermer '{name}' : {result.stderr or result.stdout}"}
        
        elif pid:
            pid = int(pid)
            log_action(f"Fermeture du processus PID={pid}")
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, text=True, timeout=15
            )
            if "SUCCESS" in result.stdout or result.returncode == 0:
                log_action(f"Processus PID={pid} fermé avec succès")
                return {"success": True, "target": pid, "method": "pid"}
            else:
                return {"error": f"Impossible de fermer PID={pid} : {result.stderr or result.stdout}"}
        
        else:
            return {"error": "Spécifiez un nom de processus (name) ou un PID (pid)."}
    
    except subprocess.TimeoutExpired:
        return {"error": "Timeout lors de la fermeture du processus"}
    except Exception as e:
        log_action(f"Erreur kill_process : {e}")
        return {"error": str(e)}


def get_battery_status():
    """
    Récupère le niveau de batterie et l'état de charge (portables uniquement).
    Retourne le pourcentage, l'état (charge/décharge/branché) et l'autonomie estimée.
    """
    try:
        ps_script = '''
        $battery = Get-WmiObject Win32_Battery | Select-Object -First 1
        if ($battery) {
            $status = switch ($battery.BatteryStatus) {
                1 { "décharge" }
                2 { "secteur (branché)" }
                3 { "pleine charge" }
                4 { "en charge" }
                5 { "critique" }
                6 { "en charge (faible)" }
                7 { "en charge (élevée)" }
                8 { "en charge (complète)" }
                default { "inconnu" }
            }
            @{
                percent = $battery.EstimatedChargeRemaining
                status = $status
                status_code = $battery.BatteryStatus
                plugged_in = ($battery.BatteryStatus -ne 1 -and $battery.BatteryStatus -ne 5)
                estimated_runtime_min = $battery.EstimatedRunTime
            } | ConvertTo-Json -Compress
        } else {
            @{error = "Aucune batterie détectée (ordinateur de bureau ?)"} | ConvertTo-Json -Compress
        }
        '''
        
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10
        )
        
        data = json.loads(result.stdout.strip())
        
        if "error" in data:
            log_action(f"Batterie : {data['error']}")
            return data
        
        percent = data.get("percent", "N/A")
        status = data.get("status", "inconnu")
        plugged = data.get("plugged_in", False)
        
        log_action(f"Batterie : {percent}% - {status}")
        return {
            "percent": percent,
            "status": status,
            "plugged_in": plugged,
            "estimated_runtime_min": data.get("estimated_runtime_min", "N/A")
        }
    
    except subprocess.TimeoutExpired:
        return {"error": "Timeout lors de la récupération du statut batterie"}
    except Exception as e:
        log_action(f"Erreur batterie : {e}")
        return {"error": str(e)}


def play_youtube(query):
    """
    Recherche une vidéo YouTube et l'ouvre dans le navigateur par défaut.
    Si un seul résultat correspond bien, ouvre directement la première vidéo.
    """
    try:
        import urllib.parse
        
        log_action(f"Recherche YouTube : '{query}'")
        encoded = urllib.parse.quote(query)
        
        # Essayer de récupérer le premier résultat via la recherche YouTube
        search_url = f"https://www.youtube.com/results?search_query={encoded}"
        
        # Tenter une recherche DuckDuckGo pour trouver l'URL directe
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(f"site:youtube.com {query}", max_results=1))
                if results and "youtube.com/watch" in results[0].get("href", ""):
                    direct_url = results[0]["href"]
                    webbrowser.open(direct_url)
                    log_action(f"YouTube ouvert : {direct_url}")
                    return {"success": True, "url": direct_url, "query": query, "method": "direct"}
        except Exception:
            pass  # Fallback sur la page de recherche
        
        # Fallback : ouvrir la page de recherche YouTube
        webbrowser.open(search_url)
        log_action(f"Page recherche YouTube ouverte : {search_url}")
        return {
            "success": True,
            "url": search_url,
            "query": query,
            "method": "search_page",
            "note": "Page de recherche YouTube ouverte. La première vidéo est en haut de la page."
        }
    
    except Exception as e:
        log_action(f"Erreur YouTube : {e}")
        return {"error": str(e)}


def text_to_file(filename, content):
    """
    Sauvegarde rapidement du texte dans un fichier .txt sur le Bureau.
    filename : nom du fichier (sans extension, .txt ajouté automatiquement).
    content : contenu textuel à enregistrer.
    """
    try:
        # Déterminer le dossier Bureau
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            desktop = os.path.join(os.path.expanduser("~"), "Bureau")
        if not os.path.exists(desktop):
            desktop = os.path.expanduser("~")  # Fallback home
        
        # Nettoyer le nom de fichier
        safe_name = "".join(c for c in filename if c.isalnum() or c in " _-")
        if not safe_name.endswith(".txt"):
            safe_name += ".txt"
        
        filepath = os.path.join(desktop, safe_name)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        size = os.path.getsize(filepath)
        log_action(f"Fichier sauvegardé : {filepath} ({size} octets)")
        
        return {
            "success": True,
            "path": filepath,
            "filename": safe_name,
            "size_bytes": size,
            "desktop_folder": desktop
        }
    except Exception as e:
        log_action(f"Erreur text_to_file : {e}")
        return {"error": str(e)}


# ============================================================================
# OUTILS DE CHANGEMENT DE VOIX TTS — L'IA peut changer de voix à la volée
# ============================================================================

# Mapping des IDs de voix Edge TTS vers des descriptions lisibles pour l'IA
VOICE_DESCRIPTIONS = {
    "fr-FR-HenriNeural":       "Henri — voix masculine française, chaleureuse et naturelle",
    "fr-FR-DeniseNeural":      "Denise — voix féminine française, claire et professionnelle",
    "fr-FR-HortenseNeural":    "Hortense — voix féminine française, douce et naturelle",
    "fr-FR-CelesteNeural":     "Céleste — voix féminine française, jeune et dynamique",
    "fr-FR-ClaudeNeural":      "Claude — voix masculine française, posée et mature",
    "fr-FR-AlainNeural":       "Alain — voix masculine française, grave et autoritaire",
    "fr-FR-VivienneMultilingualNeural": "Vivienne — voix féminine multilingue, élégante",
    "fr-FR-RemyMultilingualNeural":     "Rémy — voix masculine multilingue, conviviale",
    "fr-CA-AntoineNeural":     "Antoine — voix masculine canadienne-française",
    "fr-CA-JeanNeural":        "Jean — voix masculine canadienne-française, rassurante",
    "fr-CA-SylvieNeural":      "Sylvie — voix féminine canadienne-française, amicale",
    "fr-CH-ArianeNeural":      "Ariane — voix féminine suisse romande, distinguée",
    "fr-CH-FabriceNeural":     "Fabrice — voix masculine suisse romande, soignée",
    "fr-BE-CharlineNeural":    "Charline — voix féminine belge francophone, pétillante",
    "fr-BE-GerardNeural":      "Gérard — voix masculine belge francophone, chaleureuse",
    "en-US-AriaNeural":        "Aria — voix féminine anglaise (US), naturelle",
    "en-US-GuyNeural":         "Guy — voix masculine anglaise (US), énergique",
    "en-US-JennyNeural":       "Jenny — voix féminine anglaise (US), amicale",
    "en-GB-SoniaNeural":       "Sonia — voix féminine anglaise (UK), élégante",
    "en-GB-RyanNeural":        "Ryan — voix masculine anglaise (UK), posée",
}

VOICE_GENDERS = {
    "fr-FR-HenriNeural": "male", "fr-FR-DeniseNeural": "female", "fr-FR-HortenseNeural": "female",
    "fr-FR-CelesteNeural": "female", "fr-FR-ClaudeNeural": "male", "fr-FR-AlainNeural": "male",
    "fr-FR-VivienneMultilingualNeural": "female", "fr-FR-RemyMultilingualNeural": "male",
    "fr-CA-AntoineNeural": "male", "fr-CA-JeanNeural": "male", "fr-CA-SylvieNeural": "female",
    "fr-CH-ArianeNeural": "female", "fr-CH-FabriceNeural": "male",
    "fr-BE-CharlineNeural": "female", "fr-BE-GerardNeural": "male",
    "en-US-AriaNeural": "female", "en-US-GuyNeural": "male", "en-US-JennyNeural": "female",
    "en-GB-SoniaNeural": "female", "en-GB-RyanNeural": "male",
}


def switch_tts_voice(voice_id=None, gender=None, accent=None):
    """
    Change la voix de synthèse vocale (TTS) de l'assistant en temps réel.
    
    Paramètres (au moins un doit être fourni) :
    - voice_id : ID exact de la voix Edge TTS (ex: 'fr-FR-DeniseNeural', 'fr-FR-HenriNeural')
    - gender : 'male' pour voix masculine, 'female' pour voix féminine
    - accent : 'france', 'canada', 'suisse', 'belgique', 'anglais_us', 'anglais_uk'
    
    Si voice_id est fourni, il est utilisé directement.
    Sinon, gender et/ou accent servent à filtrer les voix disponibles.
    """
    if not _voice_manager:
        return {"error": "Gestionnaire vocal non initialisé. Le changement de voix n'est pas disponible."}
    
    try:
        # Si un voice_id exact est fourni, on l'utilise directement
        if voice_id and voice_id in VOICE_DESCRIPTIONS:
            _voice_manager.edge_voice = voice_id
            _voice_manager.tts_provider = "edge"  # Forcer Edge TTS pour les voix neurales
            voice_name = VOICE_DESCRIPTIONS.get(voice_id, voice_id)
            log_action(f"Voix TTS changée → {voice_name}")
            return {
                "success": True,
                "voice_id": voice_id,
                "description": voice_name,
                "gender": VOICE_GENDERS.get(voice_id, "unknown")
            }
        
        # Sinon, on cherche parmi toutes les voix disponibles selon les critères
        candidates = []
        for vid, desc in VOICE_DESCRIPTIONS.items():
            # Filtrer par langue (priorité français)
            if not vid.startswith("fr-") and not vid.startswith("en-"):
                continue
            
            match = True
            if gender:
                if VOICE_GENDERS.get(vid) != gender:
                    match = False
            if accent:
                acc_lower = accent.lower()
                acc_map = {
                    "france": "fr-FR", "canada": "fr-CA", "canadien": "fr-CA",
                    "suisse": "fr-CH", "belgique": "fr-BE", "belge": "fr-BE",
                    "anglais_us": "en-US", "anglais_uk": "en-GB",
                    "us": "en-US", "uk": "en-GB"
                }
                prefix = acc_map.get(acc_lower, "")
                if prefix and not vid.startswith(prefix):
                    match = False
            if match:
                candidates.append(vid)
        
        if not candidates:
            # Fallback : prendre la première voix française disponible
            for vid in VOICE_DESCRIPTIONS:
                if vid.startswith("fr-FR"):
                    candidates.append(vid)
                    break
        
        if not candidates:
            return {"error": "Aucune voix ne correspond aux critères spécifiés."}
        
        # Prendre la première voix candidate (on pourrait affiner avec un tri)
        chosen = candidates[0]
        _voice_manager.edge_voice = chosen
        _voice_manager.tts_provider = "edge"
        voice_name = VOICE_DESCRIPTIONS.get(chosen, chosen)
        
        log_action(f"Voix TTS changée → {voice_name}")
        return {
            "success": True,
            "voice_id": chosen,
            "description": voice_name,
            "gender": VOICE_GENDERS.get(chosen, "unknown"),
            "candidates_considered": len(candidates)
        }
        
    except Exception as e:
        log_action(f"Erreur changement de voix : {e}")
        return {"error": f"Impossible de changer la voix : {str(e)}"}


def get_available_voices():
    """
    Retourne la liste de toutes les voix TTS disponibles que l'assistant peut utiliser.
    L'IA peut appeler cet outil pour connaître les options avant d'en choisir une.
    """
    voices = []
    for vid, desc in VOICE_DESCRIPTIONS.items():
        voices.append({
            "id": vid,
            "description": desc,
            "gender": VOICE_GENDERS.get(vid, "unknown"),
            "language": vid[:5]  # fr-FR, fr-CA, en-US, etc.
        })
    
    current_voice = _voice_manager.edge_voice if _voice_manager else "inconnue"
    log_action(f"Liste des voix disponibles ({len(voices)} voix). Voix actuelle : {current_voice}")
    
    return {
        "current_voice": current_voice,
        "total_voices": len(voices),
        "voices": voices
    }


# ============================================================================
# OUTILS ÉTENDUS — Contrôle système, réseau, fichiers, multimédia, sécurité
# ============================================================================

def lock_screen():
    """Verrouille la session Windows (Win+L)."""
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        log_action("Session verrouillée.")
        return {"success": True, "message": "Session verrouillée."}
    except Exception as e:
        log_action(f"Erreur lock_screen : {e}")
        return {"error": str(e)}


def sleep_computer():
    """Met l'ordinateur en veille."""
    try:
        subprocess.run(["powershell", "-Command", "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"], capture_output=True, timeout=10)
        log_action("PC mis en veille.")
        return {"success": True, "message": "PC mis en veille."}
    except Exception as e:
        log_action(f"Erreur sleep_computer : {e}")
        return {"error": str(e)}


def restart_computer(delay_seconds=30):
    """Redémarre le PC après délai (défaut 30s)."""
    try:
        subprocess.run(f"shutdown /r /t {int(delay_seconds)} /c \"Redemarrage par l'assistant IA\"", shell=True, capture_output=True, timeout=5)
        log_action(f"Redemarrage programme dans {delay_seconds}s.")
        return {"success": True, "message": f"Redemarrage dans {delay_seconds}s. shutdown /a pour annuler."}
    except Exception as e:
        log_action(f"Erreur restart_computer : {e}")
        return {"error": str(e)}


def shutdown_computer(delay_seconds=60):
    """Eteint le PC apres delai (defaut 60s)."""
    try:
        subprocess.run(f"shutdown /s /t {int(delay_seconds)} /c \"Arret par l'assistant IA\"", shell=True, capture_output=True, timeout=5)
        log_action(f"Arret programme dans {delay_seconds}s.")
        return {"success": True, "message": f"Arret dans {delay_seconds}s. shutdown /a pour annuler."}
    except Exception as e:
        log_action(f"Erreur shutdown_computer : {e}")
        return {"error": str(e)}


def get_wifi_info():
    """Recupere le nom et signal du reseau WiFi actuel."""
    try:
        r1 = subprocess.run(["powershell", "-Command", "(Get-NetConnectionProfile | Where-Object {$_.IPv4Connectivity -eq 'Internet'}).Name"], capture_output=True, text=True, timeout=10)
        ssid = r1.stdout.strip() or "Inconnu"
        r2 = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=10)
        signal = "Inconnue"
        for line in r2.stdout.split("\n"):
            if "Signal" in line and ":" in line:
                signal = line.split(":")[-1].strip()
                break
        log_action(f"WiFi : {ssid} (signal: {signal})")
        return {"ssid": ssid, "signal": signal}
    except Exception as e:
        log_action(f"Erreur get_wifi_info : {e}")
        return {"error": str(e)}


def get_bluetooth_devices():
    """Liste les appareils Bluetooth."""
    try:
        result = subprocess.run(["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | Select-Object FriendlyName, Status | Format-Table -HideTableHeaders"], capture_output=True, text=True, timeout=10)
        lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
        devices = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                name = " ".join(parts[:-1])
                status = parts[-1]
                devices.append({"name": name, "status": status})
        log_action(f"Bluetooth : {len(devices)} appareil(s).")
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        log_action(f"Erreur get_bluetooth_devices : {e}")
        return {"error": str(e)}


def get_installed_apps(filter_name=None, top=20):
    """Liste les applications installees sur le PC."""
    try:
        ps_cmd = "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Where-Object {$_.DisplayName} | Select-Object -ExpandProperty DisplayName"
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=20)
        apps = [a.strip() for a in result.stdout.split("\n") if a.strip()]
        if filter_name:
            apps = [a for a in apps if filter_name.lower() in a.lower()]
        apps = apps[:min(top, 50)]
        log_action(f"Applications : {len(apps)} trouvee(s)" + (f" (filtre: {filter_name})" if filter_name else ""))
        return {"apps": apps, "count": len(apps)}
    except Exception as e:
        log_action(f"Erreur get_installed_apps : {e}")
        return {"error": str(e)}


def rename_file(path, new_name):
    """Renomme un fichier ou dossier."""
    try:
        if not os.path.exists(path):
            return {"error": f"Fichier introuvable : {path}"}
        parent = os.path.dirname(path) or "."
        new_path = os.path.join(parent, new_name)
        os.rename(path, new_path)
        log_action(f"Renomme : {os.path.basename(path)} -> {new_name}")
        return {"success": True, "old_path": path, "new_path": new_path}
    except Exception as e:
        log_action(f"Erreur rename_file : {e}")
        return {"error": str(e)}


def move_file(source, destination):
    """Deplace un fichier ou dossier."""
    try:
        if not os.path.exists(source):
            return {"error": f"Source introuvable : {source}"}
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        shutil.move(source, destination)
        log_action(f"Deplace : {source} -> {destination}")
        return {"success": True, "source": source, "destination": destination}
    except Exception as e:
        log_action(f"Erreur move_file : {e}")
        return {"error": str(e)}


def copy_file(source, destination):
    """Copie un fichier ou dossier (recursif)."""
    try:
        if not os.path.exists(source):
            return {"error": f"Source introuvable : {source}"}
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        if os.path.isdir(source):
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
        log_action(f"Copie : {source} -> {destination}")
        return {"success": True, "source": source, "destination": destination}
    except Exception as e:
        log_action(f"Erreur copy_file : {e}")
        return {"error": str(e)}


def search_files_on_disk(query, search_path=None, max_results=20):
    """Recherche des fichiers par nom sur le disque."""
    try:
        if not search_path:
            search_path = os.path.expanduser("~")
        ps_cmd = f"Get-ChildItem -Path '{search_path}' -Recurse -Filter '*{query}*' -ErrorAction SilentlyContinue | Select-Object -First {max_results} FullName, Length, LastWriteTime | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=30)
        try:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
        except:
            data = []
        results = [{"path": item["FullName"], "size_bytes": item.get("Length", 0), "modified": str(item.get("LastWriteTime", ""))} for item in data if item and "FullName" in item]
        log_action(f"Recherche '{query}' : {len(results)} resultat(s).")
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        log_action(f"Erreur search_files_on_disk : {e}")
        return {"error": str(e)}


def get_file_size(path):
    """Calcule la taille d'un fichier ou dossier."""
    try:
        if not os.path.exists(path):
            return {"error": f"Chemin introuvable : {path}"}
        if os.path.isfile(path):
            size_bytes = os.path.getsize(path)
            fcount = 1
        else:
            total = 0
            fcount = 0
            for dirpath, _, filenames in os.walk(path):
                for fn in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, fn))
                        fcount += 1
                    except:
                        pass
            size_bytes = total
        if size_bytes < 1024:
            readable = f"{size_bytes} octets"
        elif size_bytes < 1048576:
            readable = f"{size_bytes/1024:.1f} Ko"
        elif size_bytes < 1073741824:
            readable = f"{size_bytes/1048576:.1f} Mo"
        else:
            readable = f"{size_bytes/1073741824:.2f} Go"
        log_action(f"Taille de {path} : {readable}")
        return {"path": path, "size_bytes": size_bytes, "size_readable": readable, "file_count": fcount, "is_directory": os.path.isdir(path)}
    except Exception as e:
        log_action(f"Erreur get_file_size : {e}")
        return {"error": str(e)}


def compress_folder(folder_path, zip_path=None):
    """Compresse un dossier en ZIP."""
    try:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return {"error": f"Dossier introuvable ou non valide : {folder_path}"}
        if not zip_path:
            zip_path = folder_path.rstrip("\\/") + ".zip"
        if not zip_path.lower().endswith(".zip"):
            zip_path += ".zip"
        base_name = zip_path[:-4]
        root_dir = folder_path
        base_dir = os.path.basename(folder_path.rstrip("\\/"))
        shutil.make_archive(base_name, 'zip', root_dir=os.path.dirname(folder_path), base_dir=base_dir)
        zip_size = os.path.getsize(zip_path)
        log_action(f"Compresse : {folder_path} -> {zip_path} ({zip_size} octets)")
        return {"success": True, "zip_path": zip_path, "size_bytes": zip_size}
    except Exception as e:
        log_action(f"Erreur compress_folder : {e}")
        return {"error": str(e)}


def play_music_local(filepath):
    """Joue un fichier audio local avec le lecteur par defaut."""
    try:
        if not os.path.exists(filepath):
            return {"error": f"Fichier audio introuvable : {filepath}"}
        os.startfile(filepath)
        log_action(f"Lecture audio : {filepath}")
        return {"success": True, "filepath": filepath, "message": "Lecture demarree."}
    except Exception as e:
        log_action(f"Erreur play_music_local : {e}")
        return {"error": str(e)}


def stop_music():
    """Arrete toute lecture audio en fermant les lecteurs connus."""
    try:
        players = ["wmplayer.exe", "music.ui.exe", "spotify.exe", "vlc.exe"]
        killed = []
        for p in players:
            try:
                subprocess.run(["taskkill", "/F", "/IM", p], capture_output=True, timeout=3)
                killed.append(p)
            except:
                pass
        log_action(f"Musique arretee : {killed if killed else 'aucun'}")
        return {"success": True, "stopped_players": killed, "message": "Lecture audio arretee." if killed else "Aucun lecteur audio trouve."}
    except Exception as e:
        log_action(f"Erreur stop_music : {e}")
        return {"error": str(e)}


def system_brightness(action="get", level=None):
    """Lit ou modifie la luminosite de l'ecran (0-100%)."""
    try:
        if action == "get":
            result = subprocess.run(["powershell", "-Command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"], capture_output=True, text=True, timeout=10)
            try:
                brightness = int(result.stdout.strip())
            except:
                brightness = -1
            log_action(f"Luminosite actuelle : {brightness}%")
            return {"brightness": brightness, "message": f"Luminosite : {brightness}%"}
        elif action == "set" and level is not None:
            level = max(0, min(100, int(level)))
            subprocess.run(["powershell", "-Command", f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(0,{level})"], capture_output=True, timeout=10)
            log_action(f"Luminosite reglee a {level}%")
            return {"success": True, "brightness": level, "message": f"Luminosite reglee a {level}%"}
        return {"error": "Utiliser 'get' ou 'set' avec un niveau 0-100."}
    except Exception as e:
        log_action(f"Erreur system_brightness : {e}")
        return {"error": str(e)}


def take_webcam_photo(filepath=None):
    """Prend une photo avec la webcam (100% local, 0 cloud)."""
    try:
        if not filepath:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, f"webcam_{time.strftime('%Y%m%d_%H%M%S')}.png")
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Start-Process microsoft.windows.camera: -WindowStyle Maximized
Start-Sleep -Seconds 3
[System.Windows.Forms.SendKeys]::SendWait('^(c)')
Start-Sleep -Seconds 1
$img = [System.Windows.Forms.Clipboard]::GetImage()
if ($img) {{ $img.Save('{filepath}', [System.Drawing.Imaging.ImageFormat]::Png); Write-Output 'OK' }}
else {{ Write-Output 'NO_IMAGE' }}
Start-Sleep -Seconds 1
Stop-Process -Name WindowsCamera -Force -ErrorAction SilentlyContinue
"""
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, timeout=20)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            log_action(f"Photo webcam : {filepath}")
            return {"success": True, "filepath": filepath, "message": "Photo prise et sauvegardee localement."}
        return {"error": "Impossible de capturer la webcam."}
    except Exception as e:
        log_action(f"Erreur take_webcam_photo : {e}")
        return {"error": str(e)}


def get_public_ip():
    """Recupere l'adresse IP publique (ipify.org)."""
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        ip = data.get("ip", "Inconnue")
        log_action(f"IP publique : {ip}")
        return {"ip": ip}
    except Exception as e:
        log_action(f"Erreur get_public_ip : {e}")
        return {"error": str(e)}


def speed_test():
    """Test de debit Internet."""
    try:
        result = subprocess.run(["powershell", "-Command", "try { $r = Invoke-WebRequest -Uri 'http://speedtest.tele2.net/1MB.zip' -UseBasicParsing; $s = [math]::Round($r.Content.Length / 1048576.0 * 8, 2); $s } catch { '0' }"], capture_output=True, text=True, timeout=30)
        try:
            speed_mbps = float(result.stdout.strip())
        except:
            speed_mbps = 0
        log_action(f"Test debit : {speed_mbps} Mbps")
        return {"speed_mbps": speed_mbps, "message": f"Debit estime : {speed_mbps} Mbps"} if speed_mbps > 0 else {"error": "Impossible de mesurer le debit."}
    except Exception as e:
        log_action(f"Erreur speed_test : {e}")
        return {"error": str(e)}


def ping_host(host, count=4):
    """Ping un hote et retourne la latence."""
    try:
        result = subprocess.run(["ping", "-n", str(min(count, 10)), host], capture_output=True, text=True, timeout=15)
        output = result.stdout
        stats = {}
        for line in output.split("\n"):
            if "Minimum" in line or "Moyenne" in line or "Average" in line:
                parts = line.split(",")
                for p in parts:
                    if "ms" in p:
                        kv = p.strip().split("=")
                        if len(kv) == 2:
                            stats[kv[0].strip()] = kv[1].strip()
        loss = "0%"
        for line in output.split("\n"):
            if "(" in line and "%" in line:
                loss = line[line.find("(")+1:line.find("%")+1]
        reachable = "ms" in output.lower() or "time" in output.lower()
        log_action(f"Ping {host} : {'OK' if reachable else 'echec'}")
        return {"host": host, "reachable": reachable, "loss": loss, "stats": stats}
    except Exception as e:
        log_action(f"Erreur ping_host : {e}")
        return {"error": str(e)}


def dns_lookup(domain):
    """Resolution DNS d'un nom de domaine."""
    try:
        import socket
        ips = socket.getaddrinfo(domain, None)
        ip_list = list(set([addr[4][0] for addr in ips]))
        log_action(f"DNS {domain} : {', '.join(ip_list)}")
        return {"domain": domain, "ips": ip_list, "count": len(ip_list)}
    except Exception as e:
        log_action(f"Erreur dns_lookup : {e}")
        return {"error": str(e)}


def scan_local_network():
    """Scan les appareils sur le reseau local via ARP."""
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
        devices = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line and ("dynamique" in line.lower() or "dynamic" in line.lower() or "statique" in line.lower() or "static" in line.lower()):
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    mac = parts[1] if len(parts) > 1 else "inconnue"
                    if mac.count("-") == 5:
                        devices.append({"ip": ip, "mac": mac})
        log_action(f"Scan reseau : {len(devices)} appareil(s).")
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        log_action(f"Erreur scan_local_network : {e}")
        return {"error": str(e)}


def create_calendar_event(title, date_str, time_str="09:00", duration_minutes=60, description=""):
    """Cree un evenement calendrier (fichier ICS)."""
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        ics_path = os.path.join(desktop, f"event_{title[:20].replace(' ', '_')}.ics")
        date_clean = date_str.replace("-", "").replace("/", "")
        time_clean = time_str.replace(":", "") + "00"
        dt_start = f"{date_clean}T{time_clean}"
        h, m = int(time_str.split(":")[0]), int(time_str.split(":")[1])
        end_h = h + (m + duration_minutes) // 60
        end_m = (m + duration_minutes) % 60
        dt_end = f"{date_clean}T{end_h:02d}{end_m:02d}00"
        ics = f"BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//AssistantIA//FR\nBEGIN:VEVENT\nDTSTART:{dt_start}\nDTEND:{dt_end}\nSUMMARY:{title}\nDESCRIPTION:{description}\nEND:VEVENT\nEND:VCALENDAR"
        with open(ics_path, "w", encoding="utf-8") as f:
            f.write(ics)
        os.startfile(ics_path)
        subprocess.run(["start", "outlookcal:"], shell=True, capture_output=True)
        log_action(f"Evenement : {title} le {date_str} a {time_str}")
        return {"success": True, "title": title, "date": date_str, "time": time_str, "duration_minutes": duration_minutes, "ics_file": ics_path}
    except Exception as e:
        log_action(f"Erreur create_calendar_event : {e}")
        return {"error": str(e)}


def get_today_events():
    """Recupere les evenements du jour depuis Outlook."""
    try:
        ps_cmd = "$cal = New-Object -ComObject Outlook.Application; $ns = $cal.GetNamespace('MAPI'); $folder = $ns.GetDefaultFolder(9); $today = [datetime]::Today; $items = $folder.Items | Where-Object { $_.Start -ge $today -and $_.Start -lt $today.AddDays(1) } | Sort-Object Start; $items | ForEach-Object { \"$($_.Subject)|$($_.Start.ToString('HH:mm'))|$($_.End.ToString('HH:mm'))|$($_.Location)\" }"
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=15)
        events = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    events.append({"title": parts[0], "start": parts[1], "end": parts[2], "location": parts[3] if len(parts) > 3 else ""})
        log_action(f"Evenements du jour : {len(events)}")
        return {"events": events, "count": len(events), "date": time.strftime("%Y-%m-%d")}
    except Exception as e:
        log_action(f"Erreur get_today_events : {e}")
        return {"error": str(e)}


def start_timer_pomodoro(work_minutes=25, break_minutes=5, cycles=1):
    """Lance un minuteur Pomodoro en arriere-plan."""
    try:
        def _pomodoro():
            for c in range(int(cycles)):
                log_action(f"Pomodoro cycle {c+1}/{cycles} : travail {work_minutes} min")
                time.sleep(int(work_minutes) * 60)
                try:
                    subprocess.run(["powershell", "-Command", f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Pause de {break_minutes} minutes !', 'Pomodoro', 'OK', 'Information')"], capture_output=True, timeout=5)
                except:
                    pass
                log_action(f"Pomodoro cycle {c+1}/{cycles} : pause {break_minutes} min")
                if c < int(cycles) - 1:
                    time.sleep(int(break_minutes) * 60)
        t = threading.Thread(target=_pomodoro, daemon=True)
        t.start()
        log_action(f"Pomodoro : {cycles} cycle(s) {work_minutes}+{break_minutes} min")
        return {"success": True, "work_minutes": work_minutes, "break_minutes": break_minutes, "cycles": cycles, "message": f"Pomodoro lance ! {cycles} cycle(s) de {work_minutes} min travail + {break_minutes} min pause."}
    except Exception as e:
        log_action(f"Erreur pomodoro : {e}")
        return {"error": str(e)}


def encrypt_file(filepath, password, action="encrypt"):
    """Chiffre/dechiffre un fichier avec mot de passe (AES-256, PowerShell)."""
    try:
        if not os.path.exists(filepath):
            return {"error": f"Fichier introuvable : {filepath}"}
        if action == "encrypt":
            out = filepath + ".encrypted"
            ps_cmd = f"$k=[System.Text.Encoding]::UTF8.GetBytes('{password}'.PadRight(32).Substring(0,32));$c=[System.IO.File]::ReadAllBytes('{filepath}');$a=[System.Security.Cryptography.Aes]::Create();$a.Key=$k;$a.Mode=[System.Security.Cryptography.CipherMode]::CBC;$a.GenerateIV();$e=$a.CreateEncryptor().TransformFinalBlock($c,0,$c.Length);$r=$a.IV+$e;[System.IO.File]::WriteAllBytes('{out}',$r);Write-Output 'OK'"
        elif action == "decrypt":
            if not filepath.endswith(".encrypted"):
                return {"error": "Le fichier doit avoir l'extension .encrypted"}
            out = filepath[:-10]
            ps_cmd = f"$k=[System.Text.Encoding]::UTF8.GetBytes('{password}'.PadRight(32).Substring(0,32));$d=[System.IO.File]::ReadAllBytes('{filepath}');$iv=$d[0..15];$ed=$d[16..($d.Length-1)];$a=[System.Security.Cryptography.Aes]::Create();$a.Key=$k;$a.IV=$iv;$a.Mode=[System.Security.Cryptography.CipherMode]::CBC;$dec=$a.CreateDecryptor().TransformFinalBlock($ed,0,$ed.Length);[System.IO.File]::WriteAllBytes('{out}',$dec);Write-Output 'OK'"
        else:
            return {"error": "Action invalide. Utiliser 'encrypt' ou 'decrypt'."}
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=30)
        if "OK" in result.stdout:
            log_action(f"Fichier {action}e : {filepath} -> {out}")
            return {"success": True, "action": action, "input": filepath, "output": out}
        return {"error": f"Echec du {action}."}
    except Exception as e:
        log_action(f"Erreur encrypt_file : {e}")
        return {"error": str(e)}


def clear_browser_cache(browser="all"):
    """Vide le cache des navigateurs (Chrome, Edge, Firefox) - 100% local."""
    try:
        cleared = []
        browsers_to_clear = [browser] if browser != "all" else ["chrome", "edge", "firefox"]
        for b in browsers_to_clear:
            try:
                if b == "chrome":
                    cache_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data", "Default", "Cache")
                    if os.path.exists(cache_path):
                        shutil.rmtree(cache_path, ignore_errors=True)
                        cleared.append("Chrome")
                elif b == "edge":
                    cache_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data", "Default", "Cache")
                    if os.path.exists(cache_path):
                        shutil.rmtree(cache_path, ignore_errors=True)
                        cleared.append("Edge")
                elif b == "firefox":
                    profile_path = os.path.join(os.environ.get("APPDATA", ""), "Mozilla", "Firefox", "Profiles")
                    if os.path.exists(profile_path):
                        for profile in os.listdir(profile_path):
                            if profile.endswith(".default-release") or profile.endswith(".default"):
                                cache_path = os.path.join(profile_path, profile, "cache2")
                                if os.path.exists(cache_path):
                                    shutil.rmtree(cache_path, ignore_errors=True)
                        cleared.append("Firefox")
            except Exception as ex:
                log_action(f"Erreur clearing {b} : {ex}")
        log_action(f"Cache vide : {', '.join(cleared) if cleared else 'aucun'}")
        return {"success": True, "cleared_browsers": cleared, "message": f"Cache vide pour : {', '.join(cleared)}" if cleared else "Aucun cache trouve."}
    except Exception as e:
        log_action(f"Erreur clear_browser_cache : {e}")
        return {"error": str(e)}


def show_firewall_rules(filter_name=None, top=20):
    """Affiche les regles du pare-feu Windows Defender."""
    try:
        if filter_name:
            ps_cmd = f"Get-NetFirewallRule -Enabled True | Where-Object {{$_.DisplayName -like '*{filter_name}*'}} | Select-Object -First {top} DisplayName, Direction, Action, Protocol | ConvertTo-Json"
        else:
            ps_cmd = f"Get-NetFirewallRule -Enabled True | Select-Object -First {top} DisplayName, Direction, Action, Protocol | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=15)
        try:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
        except:
            data = []
        rules = [{"name": item["DisplayName"], "direction": item.get("Direction", "?"), "action": item.get("Action", "?"), "protocol": item.get("Protocol", "Tous")} for item in data if item and "DisplayName" in item]
        log_action(f"Pare-feu : {len(rules)} regle(s).")
        return {"rules": rules, "count": len(rules)}
    except Exception as e:
        log_action(f"Erreur show_firewall_rules : {e}")
        return {"error": str(e)}


def qr_code(data, filepath=None):
    """Genere un QR code PNG (100% local, via qrcode lib)."""
    try:
        if not filepath:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, f"qrcode_{int(time.time())}.png")
        try:
            import qrcode as qrcode_lib
            img = qrcode_lib.make(data)
            img.save(filepath)
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "qrcode[pil]", "-q"], capture_output=True, timeout=30)
            import qrcode as qrcode_lib
            img = qrcode_lib.make(data)
            img.save(filepath)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            os.startfile(filepath)
            log_action(f"QR code genere : {filepath}")
            return {"success": True, "filepath": filepath, "data_preview": data[:50], "message": "QR code genere et ouvert."}
        return {"error": "Echec de la generation du QR code."}
    except Exception as e:
        log_action(f"Erreur qr_code : {e}")
        return {"error": str(e)}


def qr_reader_from_screenshot():
    """Capture l'ecran et lit un QR code visible (100% local, 0 cloud)."""
    try:
        screenshot_path = os.path.join(tempfile.gettempdir(), f"qr_scan_{int(time.time())}.png")
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
        except:
            subprocess.run(["powershell", "-Command", f"Add-Type -AssemblyName System.Windows.Forms; $b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;$bmp=New-Object System.Drawing.Bitmap($b.Width,$b.Height);$g=[System.Drawing.Graphics]::FromImage($bmp);$g.CopyFromScreen(0,0,0,0,$b.Size);$bmp.Save('{screenshot_path}',[System.Drawing.Imaging.ImageFormat]::Png)"], capture_output=True, timeout=10)
        qr_data = None
        try:
            from PIL import Image
            from pyzbar.pyzbar import decode
            img = Image.open(screenshot_path)
            decoded = decode(img)
            if decoded:
                qr_data = decoded[0].data.decode("utf-8")
        except ImportError:
            pass
        if not qr_data:
            try:
                import cv2
                detector = cv2.QRCodeDetector()
                img = cv2.imread(screenshot_path)
                data, _, _ = detector.detectAndDecode(img)
                if data:
                    qr_data = data
            except ImportError:
                pass
        try:
            os.remove(screenshot_path)
        except:
            pass
        if qr_data:
            log_action(f"QR code detecte : {qr_data[:100]}")
            return {"success": True, "data": qr_data, "message": f"QR code lu : {qr_data[:80]}{'...' if len(qr_data) > 80 else ''}"}
        return {"success": False, "data": None, "message": "Aucun QR code detecte a l'ecran."}
    except Exception as e:
        log_action(f"Erreur qr_reader_from_screenshot : {e}")
        return {"error": str(e)}
