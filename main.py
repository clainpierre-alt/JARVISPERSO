import os
import logging
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from openai import OpenAI
from mem0 import MemoryClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler()])
logger = logging.getLogger("ONYX_CORE")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="ONYX // Secure HUD")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")
ACCESS_CODE = os.getenv("ACCESS_CODE", "0000")
JWT_SECRET = os.getenv("JWT_SECRET", "onyx_secure_key_2026")
JWT_ALGORITHM = "HS256"

# Modèle cible OpenCode
PRIMARY_MODEL = os.getenv("AI_MODEL_NAME", "gemini-3.5-flash-lite")
FALLBACK_MODEL = f"opencode/{PRIMARY_MODEL}" if not PRIMARY_MODEL.startswith("opencode/") else PRIMARY_MODEL

client_ai = OpenAI(api_key=OPENCODE_API_KEY, base_url="https://api.opencode.ai/v1") if OPENCODE_API_KEY else None
memory_client = MemoryClient(api_key=MEM0_API_KEY) if MEM0_API_KEY else None

class UserInteraction(BaseModel):
    user_id: str
    text_input: str
    location: str = "Inconnu"

class AuthRequest(BaseModel):
    code: str

async def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Jeton manquant")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Jeton invalide")

@app.get("/manifest.json")
async def serve_manifest():
    if os.path.exists("manifest.json"):
        return FileResponse("manifest.json", media_type="application/manifest+json")
    return JSONResponse(content={
        "name": "Onyx Neural Assistant", "short_name": "Onyx", "start_url": "/",
        "display": "standalone", "background_color": "#02040a", "theme_color": "#02040a"
    })

@app.get("/sw.js")
async def serve_sw():
    sw_content = "self.addEventListener('install', e => self.skipWaiting()); self.addEventListener('activate', e => clients.claim()); self.addEventListener('fetch', e => e.respondWith(fetch(e.request)));"
    return Response(content=sw_content, media_type="application/javascript")

@app.post("/api/auth")
@limiter.limit("5/minute")
async def verify_auth(request: Request, req: AuthRequest):
    if req.code == ACCESS_CODE:
        expire = datetime.now(timezone.utc) + timedelta(hours=2)
        encoded_jwt = jwt.encode({"sub": "admin_onyx", "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"status": "success", "access_token": encoded_jwt}
    raise HTTPException(status_code=401, detail="Code refusé")

@app.get("/", response_class=HTMLResponse)
async def serve_hud():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#02040a">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <title>ONYX // NEURAL HUD</title>
        <style>
            :root { --primary: #00f0ff; --secondary: #7000ff; --bg-deep: #02040a; --glass: rgba(0, 240, 255, 0.03); --border-glow: rgba(0, 240, 255, 0.2); --error: #ff0055; }
            * { box-sizing: border-box; }
            body { background-color: var(--bg-deep); background-image: radial-gradient(circle at 50% 50%, #0a1128 0%, #02040a 100%), linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px); background-size: 100% 100%, 30px 30px, 30px 30px; color: var(--primary); font-family: 'Share Tech Mono', monospace; display: flex; flex-direction: column; height: 100vh; margin: 0; justify-content: center; align-items: center; text-align: center; padding: 15px; overflow: hidden; touch-action: manipulation; }
            .hud-frame { border: 1px solid var(--border-glow); background: var(--glass); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); padding: 40px 25px; border-radius: 24px; width: 100%; max-width: 480px; box-shadow: 0 0 40px rgba(0, 240, 255, 0.1), inset 0 0 20px rgba(0, 240, 255, 0.05); position: relative; transition: all 0.5s ease; }
            .hud-frame.state-listening { box-shadow: 0 0 50px rgba(0, 240, 255, 0.3), inset 0 0 30px rgba(0, 240, 255, 0.1); border-color: rgba(0, 240, 255, 0.5); }
            .hud-frame.state-processing { box-shadow: 0 0 50px rgba(112, 0, 255, 0.4), inset 0 0 30px rgba(112, 0, 255, 0.1); border-color: rgba(112, 0, 255, 0.5); }
            .hud-frame::before, .hud-frame::after { content: ''; position: absolute; width: 20px; height: 20px; border-color: var(--primary); border-style: solid; transition: border-color 0.5s ease; }
            .hud-frame::before { top: -1px; left: -1px; border-width: 2px 0 0 2px; }
            .hud-frame::after { bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }
            .pin-input { background: rgba(0, 0, 0, 0.6); border: 1px solid var(--primary); color: var(--primary); font-family: 'Share Tech Mono', monospace; font-size: 1.8rem; padding: 12px; width: 70%; text-align: center; letter-spacing: 12px; margin: 20px 0; border-radius: 8px; outline: none; }
            .error-text { color: var(--error); font-size: 0.9rem; height: 20px; margin-bottom: 10px; }
            .reactor-core { width: 100px; height: 100px; margin: 0 auto 30px auto; position: relative; display: flex; align-items: center; justify-content: center; }
            .ring { position: absolute; border-radius: 50%; border: 2px dashed rgba(0, 240, 255, 0.4); }
            .ring:nth-child(1) { width: 100px; height: 100px; border-color: var(--primary); border-width: 1px; border-style: solid; opacity: 0.2; animation: spin 12s linear infinite; }
            .ring:nth-child(2) { width: 75px; height: 75px; border-color: var(--secondary); animation: spin 8s linear infinite reverse; }
            .ring:nth-child(3) { width: 50px; height: 50px; border-color: var(--primary); animation: spin 4s linear infinite; }
            .core-center { width: 20px; height: 20px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 20px var(--primary), 0 0 40px var(--secondary); }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            h1 { letter-spacing: 6px; margin: 0 0 5px 0; font-size: 1.8rem; color: #ffffff; text-shadow: 0 0 15px rgba(0, 240, 255, 0.8); }
            .subtitle { font-size: 0.8rem; letter-spacing: 3px; color: rgba(0, 240, 255, 0.7); margin-bottom: 25px; text-transform: uppercase; }
            #status { font-size: 0.9rem; color: #94a3b8; margin-bottom: 20px; min-height: 20px; }
            .terminal-output { margin-top: 15px; font-size: 1.1rem; color: #e2e8f0; min-height: 90px; max-height: 150px; overflow-y: auto; line-height: 1.6; padding: 15px; border-left: 3px solid var(--primary); background: rgba(0, 0, 0, 0.4); text-align: left; border-radius: 0 8px 8px 0; }
            .btn-tactical { background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), rgba(112, 0, 255, 0.1)); color: var(--primary); border: 1px solid var(--primary); padding: 16px 32px; font-size: 1rem; font-family: inherit; font-weight: bold; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; margin-top: 15px; width: 100%; text-transform: uppercase; }
            .btn-tactical:hover { background: var(--primary); color: var(--bg-deep); box-shadow: 0 0 30px var(--primary); }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="hud-frame" id="lockScreen">
            <h1>ONYX</h1>
            <div class="subtitle">Secure Uplink</div>
            <input type="password" id="pinInput" class="pin-input" placeholder="****" maxlength="8">
            <div id="authError" class="error-text"></div>
            <button class="btn-tactical" onclick="authenticate()">DÉVERROUILLER</button>
        </div>

        <div class="hud-frame" id="hudFrame" style="display: none;">
            <div class="reactor-core">
                <div class="ring"></div><div class="ring"></div><div class="ring"></div><div class="core-center"></div>
            </div>
            <h1>ONYX</h1>
            <div class="subtitle">Neural Vehicle Assistant</div>
            <div id="status">Système en veille</div>
            <button class="btn-tactical" id="startBtn" onclick="initOnyx()">ACTIVER ONYX</button>
            <div class="terminal-output" id="response">En attente de paramètres...</div>
        </div>

        <script>
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js'); });
            }

            let recognition;
            let isListening = false;
            let isProcessing = false;
            let currentCoords = "Inconnu";
            let jwtToken = "";
            let availableVoices = [];

            window.speechSynthesis.onvoiceschanged = () => { availableVoices = window.speechSynthesis.getVoices(); };

            function setHUDState(state, text) {
                const hud = document.getElementById("hudFrame");
                hud.className = "hud-frame";
                if (state) hud.classList.add(`state-${state}`);
                if (text) document.getElementById("status").innerText = text;
            }

            async function authenticate() {
                const code = document.getElementById('pinInput').value;
                document.getElementById('authError').innerText = "Vérification...";
                try {
                    const res = await fetch('/api/auth', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        jwtToken = data.access_token; 
                        document.getElementById('lockScreen').style.display = 'none';
                        document.getElementById('hudFrame').style.display = 'block';
                    } else {
                        document.getElementById('authError').innerText = "CODE INCORRECT";
                    }
                } catch (e) {
                    document.getElementById('authError').innerText = "Serveur indisponible";
                }
            }

            document.getElementById('pinInput').addEventListener('keypress', e => { if (e.key === 'Enter') authenticate(); });

            function initOnyx() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) return alert("Saisie vocale non prise en charge par ce navigateur.");

                document.getElementById("startBtn").style.display = "none";
                recognition = new SpeechRecognition();
                recognition.lang = 'fr-FR'; recognition.continuous = true; recognition.interimResults = false;

                recognition.onstart = () => { if(!isProcessing) setHUDState('listening', "Écoute continue active"); };
                recognition.onresult = async (event) => {
                    const speechText = event.results[event.results.length - 1][0].transcript.trim();
                    if(speechText.length > 1) {
                        setHUDState('processing', `Traitement: "${speechText}"`);
                        isProcessing = true;
                        recognition.stop(); 
                        await sendToBackend(speechText);
                    }
                };
                recognition.onend = () => { if (isListening && !isProcessing) { try { recognition.start(); } catch (e) {} } };

                isListening = true;
                try { recognition.start(); } catch(e) {}
            }

            async function sendToBackend(text) {
                document.getElementById("response").innerText = "Liaison satellite...";
                try {
                    const response = await fetch('/api/interaction', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + jwtToken },
                        body: JSON.stringify({ user_id: "pierre_admin", text_input: text, location: currentCoords })
                    });
                    const data = await response.json();
                    document.getElementById("response").innerText = data.reply;
                    speak(data.reply);
                } catch (err) {
                    document.getElementById("response").innerText = "ALERTE : Perte de signal.";
                    restartListening();
                }
            }

            function speak(text) {
                if (!('speechSynthesis' in window)) { restartListening(); return; }
                window.speechSynthesis.cancel();
                if (availableVoices.length === 0) availableVoices = window.speechSynthesis.getVoices();

                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'fr-FR'; utterance.rate = 1.05;
                const frenchVoices = availableVoices.filter(v => v.lang.startsWith('fr'));
                if (frenchVoices.length > 0) utterance.voice = frenchVoices.find(v => v.name.includes('Google') || v.name.includes('Natural')) || frenchVoices[0];

                setHUDState('', "Onyx parle...");
                utterance.onend = restartListening;
                utterance.onerror = restartListening;
                window.speechSynthesis.speak(utterance);
            }
            
            function restartListening() {
                isProcessing = false;
                if(isListening) {
                    setHUDState('listening', "Écoute continue active");
                    try { recognition.start(); } catch(e) {}
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/interaction")
async def handle_interaction(data: UserInteraction, token_data: dict = Depends(verify_token)):
    if not client_ai:
        return JSONResponse(status_code=500, content={"status": "error", "reply": "OPENCODE_API_KEY non définie sur le serveur."})
    
    try:
        context_memories = ""
        if memory_client:
            try:
                search_results = memory_client.search(query=data.text_input, filters={'user_id': data.user_id}, limit=3)
                if search_results:
                    context_memories = "\n".join([f"- {res['memory']}" for res in search_results])
            except Exception as mem_err:
                logger.error(f"Recherche Mem0 : {mem_err}")

        system_instruction = (
            "Tu es Onyx, l'assistant IA de la Citroën C4 de Pierre. "
            "RÈGLE 1 : Parle EXCLUSIVEMENT en français. "
            "RÈGLE 2 : Ta réponse doit faire MOINS de 20 mots. "
            "Sois concis, direct et factuel.\n\n"
            f"Mémoire sur Pierre :\n{context_memories if context_memories else 'Aucun souvenir.'}"
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"[Lieu: {data.location}] {data.text_input}"}
        ]

        # Tentative 1 : Slug standard (ex: gemini-3.5-flash-lite)
        try:
            completion = client_ai.chat.completions.create(model=PRIMARY_MODEL, messages=messages, max_tokens=60, temperature=0.3)
        except openai.NotFoundError:
            # Fallback automatique 1 : Slug qualifié avec namespace (opencode/gemini-3.5-flash-lite)
            logger.warning(f"Slug {PRIMARY_MODEL} non trouvé, bascule sur {FALLBACK_MODEL}")
            completion = client_ai.chat.completions.create(model=FALLBACK_MODEL, messages=messages, max_tokens=60, temperature=0.3)

        reply = completion.strip() if isinstance(completion, str) else (completion.choices[0].message.content.strip() if hasattr(completion, 'choices') and completion.choices else "Pas de réponse.")

        if memory_client:
            try:
                memory_client.add(messages=[{"role": "user", "content": data.text_input}, {"role": "assistant", "content": reply}], user_id=data.user_id)
            except Exception:
                pass

        return {"status": "success", "reply": reply}
        
    except openai.NotFoundError:
        return JSONResponse(status_code=404, content={"status": "error", "reply": "Erreur : Modèle non répertorié sur OpenCode."})
    except Exception as e:
        logger.error(f"Erreur backend : {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "reply": "Erreur de traitement serveur."})
