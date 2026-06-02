// WebSocket connection
let ws;
const wsUrl = `ws://${window.location.host}/ws`;

// UI Elements
const alexaRing = document.getElementById('alexa-ring');
const agentStateBadge = document.getElementById('agent-state-badge');
const stateText = agentStateBadge.querySelector('.state-text');
const stateDot = agentStateBadge.querySelector('.state-dot');
const micIconInside = document.getElementById('mic-icon-inside');

const connectionStatus = document.getElementById('connection-status');
const btnManualListen = document.getElementById('btn-manual-listen');
const btnTriggerOcr = document.getElementById('btn-trigger-ocr');
const btnEmergencyStop = document.getElementById('btn-emergency-stop');
const switchContinuousListen = document.getElementById('switch-continuous-listen');

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const btnSendChat = document.getElementById('btn-send-chat');
const btnClearChat = document.getElementById('btn-clear-chat');

const consoleLogs = document.getElementById('console-logs');

// Settings Modal elements
const settingsModal = document.getElementById('settings-modal');
const btnSettingsToggle = document.getElementById('btn-settings-toggle');
const btnCloseSettings = document.getElementById('btn-close-settings');
const btnCancelSettings = document.getElementById('btn-cancel-settings');
const settingsForm = document.getElementById('settings-form');

const inputApiKey = document.getElementById('setting-api-key');
const inputBaseUrl = document.getElementById('setting-base-url');
const inputModel = document.getElementById('setting-model');
const inputWakeWord = document.getElementById('setting-wake-word');
const selectTtsProvider = document.getElementById('setting-tts-provider');
const selectEdgeVoice = document.getElementById('setting-edge-voice');
const selectVoice = document.getElementById('setting-voice');
const edgeVoiceGroup = document.getElementById('edge-voice-group');
const sapi5VoiceGroup = document.getElementById('sapi5-voice-group');
const inputRate = document.getElementById('setting-rate');
const inputRateValue = document.getElementById('setting-rate-value');
const inputVolume = document.getElementById('setting-volume');
const personaGrid = document.getElementById('persona-grid');
const inputPersonaId = document.getElementById('setting-persona-id');
const voiceSummaryState = document.getElementById('voice-summary-state');
const voiceSummaryTts = document.getElementById('voice-summary-tts');
const voiceSummaryWakeWord = document.getElementById('voice-summary-wake-word');

const toastContainer = document.getElementById('toast-container');

// State Variables
let currentAgentState = 'IDLE';
let isConnecting = false;
const DEFAULT_TTS_RATE = 120;
const STATE_LABELS = {
    IDLE: 'Repos',
    LISTENING: 'Ecoute',
    THINKING: 'Reflexion',
    EXECUTING: 'Execution',
    SPEAKING: 'Parle',
    ERROR: 'Erreur',
    CONVERSATION_ACTIVE: 'Conversation'
};

// Audio Visualizer Variables
const canvas = document.getElementById('audio-waveform');
const ctx = canvas.getContext('2d');
let animationFrameId;
let audioContext;
let analyser;
let microphone;
let javascriptNode;
let micStream;
let waveSpeed = 0.05;
let wavePhase = 0;

// Setup Canvas size
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = message;
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slide-in 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function sanitizeRate(value) {
    const parsed = parseInt(value, 10);
    if (Number.isNaN(parsed)) return DEFAULT_TTS_RATE;
    return Math.min(220, Math.max(80, parsed));
}

function getProviderLabel(provider) {
    return provider === 'edge' ? 'Edge' : 'SAPI5';
}

function formatTtsRate(rate, provider) {
    const value = sanitizeRate(rate);
    if (provider === 'edge') {
        const offset = value - 100;
        if (offset === 0) return `${value} normal`;
        return `${value} (${offset > 0 ? '+' : ''}${offset}%)`;
    }
    return `${value} ppm`;
}

function syncVoiceSummary(settings = {}) {
    const provider = settings.tts_provider || (selectTtsProvider ? selectTtsProvider.value : 'edge');
    const rate = settings.tts_rate ?? (inputRate ? inputRate.value : DEFAULT_TTS_RATE);
    const wakeWord = settings.wake_word || (inputWakeWord ? inputWakeWord.value : 'jarvis');

    if (voiceSummaryTts) {
        voiceSummaryTts.innerText = `${getProviderLabel(provider)} - ${formatTtsRate(rate, provider)}`;
    }
    if (voiceSummaryWakeWord) {
        voiceSummaryWakeWord.innerText = wakeWord || 'jarvis';
    }
}

function syncTtsRateDisplay() {
    if (!inputRate) return;
    const provider = selectTtsProvider ? selectTtsProvider.value : 'edge';
    const rate = sanitizeRate(inputRate.value);
    inputRate.value = rate;
    if (inputRateValue) {
        inputRateValue.innerText = formatTtsRate(rate, provider);
    }
    syncVoiceSummary({ tts_rate: rate, tts_provider: provider });
}

// Connect to WebSocket
function connectWebSocket() {
    if (isConnecting) return;
    isConnecting = true;
    
    console.log("Connecting to WebSocket...");
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        isConnecting = false;
        connectionStatus.innerText = "Connecté";
        connectionStatus.className = "val status-indicator online";
        showToast("Connecté au serveur de l'assistant.", "success");
        
        // Request settings & voices list
        sendMessage('get_settings', {});
        sendMessage('get_voices', {});
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const type = data.type;
        const payload = data.payload;
        
        switch (type) {
            case 'state_change':
                handleStateChange(payload.state, payload.data);
                break;
            case 'tool_log':
                appendConsoleLog(payload.message);
                break;
            case 'chat_message':
                appendChatMessage(payload.role, payload.content);
                break;
            case 'settings_data':
                fillSettingsForm(payload);
                break;
            case 'voices_list':
                fillVoicesSelect(payload);
                break;
            case 'personas_list':
                fillPersonaGrid(payload);
                break;
            case 'toast':
                showToast(payload.message, payload.level);
                break;
        }
    };
    
    ws.onclose = () => {
        isConnecting = false;
        connectionStatus.innerText = "Déconnecté";
        connectionStatus.className = "val status-indicator offline";
        handleStateChange('IDLE');
        
        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        ws.close();
    };
}

function sendMessage(type, payload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type, payload }));
    }
}

// Handle State Changes & Ring styling
function handleStateChange(state, data) {
    currentAgentState = state;
    document.body.className = `theme-dark state-${state.toLowerCase()}`;
    
    // Update badge text
    const stateLabel = STATE_LABELS[state] || state;
    stateText.innerText = stateLabel;
    if (voiceSummaryState) {
        voiceSummaryState.innerText = stateLabel;
    }
    
    // Update color indicator dot
    let dotColor = 'var(--text-muted)';
    if (state === 'IDLE') dotColor = 'var(--color-idle)';
    else if (state === 'LISTENING') dotColor = 'var(--color-listening)';
    else if (state === 'THINKING') dotColor = 'var(--color-thinking)';
    else if (state === 'EXECUTING') dotColor = 'var(--color-executing)';
    else if (state === 'SPEAKING') dotColor = 'var(--color-speaking)';
    else if (state === 'ERROR') dotColor = 'var(--color-error)';
    stateDot.style.backgroundColor = dotColor;

    // Reset animations
    cancelAnimationFrame(animationFrameId);

    if (state === 'LISTENING') {
        startMicCapture();
        animateVisualizer();
        btnManualListen.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" class="icon"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect></svg><span>Arrêter</span>`;
    } else {
        stopMicCapture();
        btnManualListen.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" class="icon"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg><span>Parler</span>`;
        
        if (state === 'SPEAKING') {
            animateProceduralWaves(8, 0.08, 'rgba(46, 196, 182, 0.6)'); // Emerald voice wave
        } else if (state === 'THINKING') {
            animateProceduralWaves(4, 0.05, 'rgba(255, 0, 127, 0.4)'); // Pink thinking wave
        } else if (state === 'EXECUTING') {
            animateProceduralWaves(3, 0.03, 'rgba(255, 159, 28, 0.4)'); // Amber execution wave
        } else {
            // IDLE / ERROR
            drawFlatLine();
        }
    }
}

// Speech Recognition & Web Audio API
async function startMicCapture() {
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        
        microphone = audioContext.createMediaStreamSource(micStream);
        microphone.connect(analyser);
    } catch (err) {
        console.warn("Could not capture microphone for visualizer:", err);
        // Fallback to procedural waves for listening if mic permission denied
        animateProceduralWaves(12, 0.15, 'rgba(0, 242, 254, 0.6)');
    }
}

function stopMicCapture() {
    if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        micStream = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
}

// Draw static flat line for IDLE
function drawFlatLine() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 2;
    ctx.stroke();
}

// Animate Waveform based on Real Microphone Input
function animateVisualizer() {
    if (currentAgentState !== 'LISTENING') return;
    
    animationFrameId = requestAnimationFrame(animateVisualizer);
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (!analyser) {
        // Draw fallback waves if mic failed
        drawProceduralWaves(12, 'rgba(0, 242, 254, 0.6)');
        return;
    }
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);
    
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'rgba(0, 242, 254, 0.8)';
    ctx.shadowBlur = 8;
    ctx.shadowColor = 'rgba(0, 242, 254, 0.5)';
    ctx.beginPath();
    
    const sliceWidth = canvas.width * 1.0 / bufferLength;
    let x = 0;
    
    for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * canvas.height / 2;
        
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
        
        x += sliceWidth;
    }
    
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
    ctx.shadowBlur = 0; // Reset shadow
}

// Procedural Sine Wave Generator for Speech/Thinking states
function animateProceduralWaves(amplitude, speed, color) {
    waveSpeed = speed;
    
    function draw() {
        if (currentAgentState === 'LISTENING' || currentAgentState === 'IDLE' || currentAgentState === 'ERROR') return;
        animationFrameId = requestAnimationFrame(draw);
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawProceduralWaves(amplitude, color);
    }
    
    draw();
}

function drawProceduralWaves(maxAmp, color) {
    wavePhase += waveSpeed;
    ctx.lineWidth = 2;
    ctx.strokeStyle = color;
    
    // Draw 3 layered waves for depth
    for (let w = 0; w < 3; w++) {
        ctx.beginPath();
        const amplitude = maxAmp * (1 - w * 0.3);
        const frequency = 0.01 + w * 0.005;
        const phaseOffset = w * Math.PI / 2;
        
        for (let x = 0; x < canvas.width; x++) {
            // Apply a bell-curve envelope so waves fade out at left and right boundaries
            const envelope = Math.sin((x / canvas.width) * Math.PI);
            const y = (canvas.height / 2) + Math.sin(x * frequency + wavePhase + phaseOffset) * amplitude * envelope;
            
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        
        ctx.stroke();
    }
}

// Console & Chat logs helpers
function appendConsoleLog(message) {
    const line = document.createElement('div');
    line.className = 'log-line';
    
    // Style line based on content
    if (message.startsWith('[OCR]')) {
        line.classList.add('tool-success');
    } else if (message.includes('Appel de l\'outil')) {
        line.classList.add('tool-call');
    } else if (message.includes('exécuté') || message.includes('terminée') || message.includes('succès')) {
        line.classList.add('tool-success');
    } else if (message.includes('Erreur') || message.includes('Échec') || message.includes('Exception')) {
        line.classList.add('tool-error');
    } else if (message.startsWith('[TTS]') || message.startsWith('[STT]')) {
        line.classList.add('tool-exec');
    } else {
        line.classList.add('system');
    }
    
    const timestamp = new Date().toLocaleTimeString();
    line.innerHTML = `<span style="color: var(--text-muted)">[${timestamp}]</span> ${escapeHtml(message)}`;
    consoleLogs.appendChild(line);
    
    // Keep console scrolled to bottom
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

function appendChatMessage(role, content) {
    const message = document.createElement('div');
    message.className = `message ${role}`;
    
    let senderName = role === 'user' ? 'Vous' : 'DeepSeek';
    if (role === 'system') senderName = 'Système';
    
    message.innerHTML = `
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; padding: 0 4px;">${senderName}</div>
        <div class="msg-content">${escapeHtml(content)}</div>
    `;
    
    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

// Form management & Settings
let suppressToggleEvent = false;

function fillSettingsForm(settings) {
    // SECURITY FIX: Only use obfuscated key for display, never the actual key
    inputApiKey.value = settings.api_key_obfuscated || '';
    inputApiKey.placeholder = 'sk-...';
    inputBaseUrl.value = settings.base_url || 'https://api.deepseek.com';
    inputModel.value = settings.model || 'deepseek-chat';
    inputWakeWord.value = settings.wake_word || 'ordinateur';
    inputRate.value = settings.tts_rate ?? DEFAULT_TTS_RATE;
    inputVolume.value = settings.tts_volume || 1.0;
    
    // TTS Provider
    if (selectTtsProvider) {
        selectTtsProvider.value = settings.tts_provider || 'edge';
        // Déclencher l'affichage du bon groupe de voix
        toggleVoiceProviderGroups();
    }
    syncTtsRateDisplay();
    syncVoiceSummary(settings);
    
    // Suppress event so we don't accidentally send toggle_continuous_listening
    suppressToggleEvent = true;
    switchContinuousListen.checked = settings.continuous_listening || false;
    suppressToggleEvent = false;
}

function fillVoicesSelect(payload) {
    // Remplir les voix SAPI5
    const sapi5Voices = payload.sapi5_voices || [];
    if (selectVoice) {
        selectVoice.innerHTML = '<option value="">Voix système par défaut</option>';
        sapi5Voices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.innerText = `${voice.name} (${voice.languages?.join(', ') || 'fr'})`;
            if (voice.id === payload.selected_sapi5_voice) {
                option.selected = true;
            }
            selectVoice.appendChild(option);
        });
    }
    
    // Remplir les voix Edge TTS
    const edgeVoices = payload.edge_voices || [];
    if (selectEdgeVoice) {
        // Grouper par langue
        const grouped = {};
        edgeVoices.forEach(voice => {
            const lang = voice.language || 'Autre';
            if (!grouped[lang]) grouped[lang] = [];
            grouped[lang].push(voice);
        });
        
        selectEdgeVoice.innerHTML = '';
        for (const [lang, voices] of Object.entries(grouped)) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = lang;
            voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.id;
                const genderIcon = voice.gender === 'Femme' ? '👩' : '👨';
                option.innerText = `${genderIcon} ${voice.name}`;
                if (voice.id === payload.selected_edge_voice) {
                    option.selected = true;
                }
                optgroup.appendChild(option);
            });
            selectEdgeVoice.appendChild(optgroup);
        }
        
        // Si aucune voix sélectionnée, sélectionner Hortense par défaut
        if (!selectEdgeVoice.value && edgeVoices.length > 0) {
            selectEdgeVoice.value = 'fr-FR-HortenseNeural';
        }
    }
    
    // Définir le bon provider TTS
    if (selectTtsProvider && payload.tts_provider) {
        selectTtsProvider.value = payload.tts_provider;
    }
    toggleVoiceProviderGroups();
    
    // Mettre à jour l'indicateur de moteur vocal
    const engineLabel = payload.tts_provider === 'edge' ? 
        (edgeVoices.length > 0 ? 'Edge TTS (Neural)' : 'Edge TTS') : 
        (sapi5Voices.length > 0 ? 'Windows SAPI5' : 'Aucun');
    document.getElementById('status-engine').innerText = engineLabel;
    syncVoiceSummary({ tts_provider: payload.tts_provider });
    syncTtsRateDisplay();
}

// Personnalités IA — remplissage du grid
function fillPersonaGrid(payload) {
    // Le backend envoie un array de personas (pas un objet)
    const personas = Array.isArray(payload.personas) ? payload.personas : [];
    const currentPersonaId = payload.current_persona_id || 'jarvis';
    const defaultPersonaId = payload.default_persona_id || 'jarvis';
    
    if (!personaGrid) return;
    
    personaGrid.innerHTML = '';
    
    // Stocker les personas globalement pour le sélecteur rapide
    window._allPersonas = personas;
    window._currentPersonaId = currentPersonaId;
    
    personas.forEach((persona) => {
        const id = persona.id;
        const card = document.createElement('div');
        card.className = 'persona-card';
        card.dataset.personaId = id;
        
        // Marquer comme sélectionné si c'est la personnalité actuelle
        if (id === currentPersonaId) {
            card.classList.add('active');
            if (inputPersonaId) inputPersonaId.value = id;
        }
        
        // Icône de la personnalité (utiliser celle définie dans personas.py)
        const emoji = persona.icon || '🤖';
        
        // Badge pour la personnalité par défaut
        let specialBadge = '';
        if (id === defaultPersonaId) {
            specialBadge = '<span class="persona-badge default-badge">Défaut</span>';
        }
        
        // Voix Edge recommandée
        const recommendedVoice = persona.recommended_edge_voice || '';
        const voiceDisplayName = recommendedVoice ? recommendedVoice.replace('fr-FR-', '').replace('fr-CA-', '').replace('fr-CH-', '').replace('fr-BE-', '').replace('Neural', '') : 'Voix système';
        
        // Construire la carte
        card.innerHTML = `
            <div class="persona-card-header">
                <span class="persona-emoji">${emoji}</span>
                <div class="persona-card-title">
                    <span class="persona-name">${escapeHtml(persona.name)}</span>
                    <span class="persona-tone">${escapeHtml(persona.description.split('.')[0])}</span>
                </div>
                ${specialBadge}
            </div>
            <div class="persona-card-desc">${escapeHtml(persona.description)}</div>
            <div class="persona-voice-hint">🗣️ Voix recommandée : ${escapeHtml(voiceDisplayName)}</div>
        `;
        
        // Gestion du clic
        card.addEventListener('click', () => {
            // Désélectionner l'ancienne
            personaGrid.querySelectorAll('.persona-card').forEach(c => c.classList.remove('active'));
            // Sélectionner la nouvelle
            card.classList.add('active');
            if (inputPersonaId) inputPersonaId.value = id;
            
            // Mettre à jour la variable globale
            window._currentPersonaId = id;
            
            // Feedback visuel
            showToast(`Personnalité "${persona.name}" sélectionnée !`, 'info');
            
            // Proposer automatiquement la voix Edge recommandée pour cette personnalité
            const recVoice = persona.recommended_edge_voice;
            if (recVoice && selectEdgeVoice) {
                // Chercher l'option correspondante dans le select
                let found = false;
                for (let opt of selectEdgeVoice.options) {
                    if (opt.value === recVoice) {
                        selectEdgeVoice.value = recVoice;
                        found = true;
                        break;
                    }
                }
                if (found) {
                    showToast(`Voix "${voiceDisplayName}" appliquée automatiquement`, 'success');
                }
            }
            
            // Mettre à jour le sélecteur rapide de personnalité dans le dashboard
            updateQuickPersonaSelector();
        });
        
        personaGrid.appendChild(card);
    });
    
    // Si aucune personnalité n'était sélectionnée, sélectionner la première
    if (inputPersonaId && !inputPersonaId.value && personas.length > 0) {
        inputPersonaId.value = personas[0].id;
        const firstCard = personaGrid.querySelector('.persona-card');
        if (firstCard) firstCard.classList.add('active');
    }
    
    // Mettre à jour le sélecteur rapide de personnalité
    updateQuickPersonaSelector();
}

// Toggle du dropdown de personnalité
document.addEventListener('DOMContentLoaded', () => {
    // Ce code s'exécute quand le DOM est chargé, mais comme le script est en fin de body,
    // on l'exécute directement via un setTimeout pour être sûr
    setTimeout(() => {
        const personaDisplay = document.getElementById('persona-current-display');
        const personaDropdown = document.getElementById('persona-dropdown-options');
        if (personaDisplay && personaDropdown) {
            personaDisplay.addEventListener('click', (e) => {
                e.stopPropagation();
                personaDropdown.classList.toggle('show');
            });
            // Fermer le dropdown quand on clique ailleurs
            document.addEventListener('click', (e) => {
                if (!personaDropdown.contains(e.target) && !personaDisplay.contains(e.target)) {
                    personaDropdown.classList.remove('show');
                }
            });
        }
    }, 500);
});

// Sélecteur rapide de personnalité dans le dashboard
function updateQuickPersonaSelector() {
    const container = document.getElementById('quick-persona-selector');
    if (!container) return;
    
    const personas = window._allPersonas || [];
    const currentId = window._currentPersonaId || 'jarvis';
    const currentPersona = personas.find(p => p.id === currentId);
    
    if (!currentPersona) return;
    
    // Mettre à jour l'affichage de la personnalité active
    const emojiEl = document.getElementById('active-persona-emoji');
    const nameEl = document.getElementById('active-persona-name');
    if (emojiEl) emojiEl.innerText = currentPersona.icon || '🤖';
    if (nameEl) nameEl.innerText = currentPersona.name;
    
    // Mettre à jour les options du dropdown
    const dropdown = document.getElementById('persona-dropdown-options');
    if (!dropdown) return;
    
    dropdown.innerHTML = '';
    personas.forEach(persona => {
        const option = document.createElement('div');
        option.className = 'persona-dropdown-item';
        if (persona.id === currentId) {
            option.classList.add('active');
        }
        option.innerHTML = `
            <span class="persona-dropdown-emoji">${persona.icon || '🤖'}</span>
            <div class="persona-dropdown-info">
                <span class="persona-dropdown-name">${escapeHtml(persona.name)}</span>
                <span class="persona-dropdown-desc">${escapeHtml(persona.description.substring(0, 60))}...</span>
            </div>
        `;
        option.addEventListener('click', () => {
            // Sélectionner cette personnalité
            window._currentPersonaId = persona.id;
            if (inputPersonaId) inputPersonaId.value = persona.id;
            
            // Mettre à jour la grille dans les paramètres (si elle est visible)
            if (personaGrid) {
                personaGrid.querySelectorAll('.persona-card').forEach(c => c.classList.remove('active'));
                const matchingCard = personaGrid.querySelector(`[data-persona-id="${persona.id}"]`);
                if (matchingCard) matchingCard.classList.add('active');
            }
            
            updateQuickPersonaSelector();
            
            // Appliquer automatiquement la voix recommandée
            const recVoice = persona.recommended_edge_voice;
            if (recVoice && selectEdgeVoice) {
                for (let opt of selectEdgeVoice.options) {
                    if (opt.value === recVoice) {
                        selectEdgeVoice.value = recVoice;
                        break;
                    }
                }
            }
            
            // Sauvegarder immédiatement le changement de personnalité
            savePersonaChange(persona.id, recVoice);
            
            showToast(`Personnalité "${persona.name}" activée !`, 'success');
        });
        dropdown.appendChild(option);
    });
}

// Sauvegarder le changement de personnalité
function savePersonaChange(personaId, recommendedVoice) {
    const updatedSettings = {
        api_key: inputApiKey ? inputApiKey.value : '',
        base_url: inputBaseUrl ? inputBaseUrl.value : 'https://api.deepseek.com',
        model: inputModel ? inputModel.value : 'deepseek-chat',
        wake_word: inputWakeWord ? inputWakeWord.value : 'jarvis',
        tts_provider: selectTtsProvider ? selectTtsProvider.value : 'edge',
        tts_voice_id: selectVoice ? selectVoice.value : '',
        tts_edge_voice: recommendedVoice || (selectEdgeVoice ? selectEdgeVoice.value : 'fr-FR-HortenseNeural'),
        tts_rate: inputRate ? sanitizeRate(inputRate.value) : DEFAULT_TTS_RATE,
        tts_volume: inputVolume ? parseFloat(inputVolume.value) : 1.0,
        persona_id: personaId,
        auto_set_voice: true,
        continuous_listening: switchContinuousListen.checked
    };
    sendMessage('save_settings', updatedSettings);
}

// Bascule visuelle entre les groupes de voix Edge vs SAPI5
function toggleVoiceProviderGroups() {
    const provider = selectTtsProvider ? selectTtsProvider.value : 'edge';
    if (edgeVoiceGroup) {
        edgeVoiceGroup.style.display = provider === 'edge' ? 'block' : 'none';
    }
    if (sapi5VoiceGroup) {
        sapi5VoiceGroup.style.display = provider === 'pyttsx3' ? 'block' : 'none';
    }
}

// Écouter le changement de provider TTS
if (selectTtsProvider) {
    selectTtsProvider.addEventListener('change', () => {
        toggleVoiceProviderGroups();
        syncTtsRateDisplay();
    });
}

if (inputRate) {
    inputRate.addEventListener('input', syncTtsRateDisplay);
}

if (inputWakeWord) {
    inputWakeWord.addEventListener('input', () => syncVoiceSummary());
}

// Event Listeners
btnSettingsToggle.addEventListener('click', () => {
    settingsModal.classList.add('active');
    sendMessage('get_personas', {});
});
btnCloseSettings.addEventListener('click', () => settingsModal.classList.remove('active'));
btnCancelSettings.addEventListener('click', () => settingsModal.classList.remove('active'));

settingsForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const updatedSettings = {
        api_key: inputApiKey.value,
        base_url: inputBaseUrl.value,
        model: inputModel.value,
        wake_word: inputWakeWord.value,
        tts_provider: selectTtsProvider ? selectTtsProvider.value : 'edge',
        tts_voice_id: selectVoice ? selectVoice.value : '',
        tts_edge_voice: selectEdgeVoice ? selectEdgeVoice.value : 'fr-FR-HortenseNeural',
        tts_rate: sanitizeRate(inputRate.value),
        tts_volume: parseFloat(inputVolume.value),
        persona_id: inputPersonaId ? inputPersonaId.value : 'jarvis',
        continuous_listening: switchContinuousListen.checked
    };
    
    sendMessage('save_settings', updatedSettings);
    settingsModal.classList.remove('active');
    showToast("Paramètres sauvegardés avec succès !", "success");
});

// Continuous Listen Switch
switchContinuousListen.addEventListener('change', () => {
    if (suppressToggleEvent) return;
    sendMessage('toggle_continuous_listening', { active: switchContinuousListen.checked });
});

// Manual Listen button
btnManualListen.addEventListener('click', () => {
    if (currentAgentState === 'LISTENING') {
        sendMessage('stop_listening', {});
    } else {
        sendMessage('start_listening', {});
    }
});

// Trigger OCR manually
btnTriggerOcr.addEventListener('click', () => {
    sendMessage('trigger_ocr_scan', {});
});

// Emergency Stop
btnEmergencyStop.addEventListener('click', () => {
    sendMessage('emergency_stop', {});
});

// Press ESC to trigger emergency stop
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        sendMessage('emergency_stop', {});
        showToast("Arrêt d'urgence envoyé !", "error");
    }
});

// Chat handlers
btnSendChat.addEventListener('click', sendChatMsg);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendChatMsg();
});

function sendChatMsg() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    appendChatMessage('user', text);
    sendMessage('user_text_command', { text });
    chatInput.value = '';
}

btnClearChat.addEventListener('click', () => {
    chatMessages.innerHTML = '';
    appendChatMessage('system', "Historique effacé.");
    sendMessage('clear_history', {});
});

// Start initialization
syncTtsRateDisplay();
connectWebSocket();
drawFlatLine();
