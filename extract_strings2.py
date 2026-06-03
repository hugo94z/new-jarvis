import re

# Ouvrir l'exe en binaire et chercher toutes les chaînes visibles
data = open(r'c:\Users\Boyz\Desktop\Nouveau dossier (13)\Installer_NouveauDossier13.exe', 'rb').read()

# Extraire les chaînes imprimables (ASCII + Latin1)
strings = []
current = b''
for b in data:
    if 32 <= b < 127:
        current += bytes([b])
    else:
        if len(current) >= 4:
            strings.append(current.decode('ascii', errors='ignore'))
        current = b''
if len(current) >= 4:
    strings.append(current.decode('ascii', errors='ignore'))

# Chercher les noms de nos modules et dépendances
patterns = [
    'fastapi', 'uvicorn', 'websockets', 'openai', 'speech_recognition',
    'edge_tts', 'pyttsx3', 'pyaudio', 'pydub', 'pyautogui', 'pillow',
    'sentence_transformers', 'pytesseract', 'flask', 'app.py', 'agent.py',
    'voice.py', 'tools_legacy', 'run_assistant', 'config.json',
    'static/index', 'static/styles', 'static/app',
    'tools/system', 'tools/files', 'tools/network', 'tools/web',
    'tools/productivity', 'tools/media', 'tools/input_tools',
    'tools/decorators', 'tools/registry', 'tools/__init__',
    'memory.py', 'personas.py', 'ocr.ps1'
]

found_all = []
for s in strings:
    s_lower = s.lower()
    for p in patterns:
        if p.lower() in s_lower:
            found_all.append(s)
            break

print("=== Fichiers/Dépendances trouvés dans l'exe ===")
for f in sorted(set(found_all)):
    print(f)

print(f"\n=== Total: {len(set(found_all))} chaînes correspondantes ===")

# Chercher aussi les noms de dossiers liés au projet
proj_names = ['Nouveau', 'dossier', 'Desktop', 'Assistant', 'Boyz']
print("\n=== Références au projet ===")
for s in strings:
    s_lower = s.lower()
    if any(n.lower() in s_lower for n in proj_names):
        print(s)