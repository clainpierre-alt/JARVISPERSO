import os
import logging
import jwt
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mem0 import MemoryClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ONYX_CORE")

# Rate Limiter & FastAPI App
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="ONYX // Vehicle HUD")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Environment Variables
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")
ACCESS_CODE = os.getenv("ACCESS_CODE", "0000")
JWT_SECRET = os.getenv("JWT_SECRET", "onyx_super_secure_jwt_secret_key_2026_c4")
JWT_ALGORITHM = "HS256"

AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "opencode/gemini-3.5-flash-lite")

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

async def call_opencode_api(system_prompt: str, user_prompt: str) -> str:
    if not OPENCODE_API_KEY:
        raise HTTPException(status_code=500, detail="OPENCODE_API_KEY non configurée")

    url = "https://api.opencode.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENCODE_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AI_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 60,
        "temperature": 0.3
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        try:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                elif isinstance(data, str):
                    return data.strip()
            logger.error(f"Erreur API OpenCode ({res.status_code}) : {res.text}")
        except Exception as err:
            logger.error(f"Erreur réseau OpenCode : {err}")

    raise HTTPException(status_code=502, detail="Impossible d'obtenir une réponse de l'API AI.")

@app.get("/manifest.json")
async def serve_manifest():
    if os.path.exists("manifest.json"):
        return FileResponse("manifest.json", media_type="application/manifest+json")
    return JSONResponse(content={"name": "Onyx", "short_name": "Onyx", "start_url": "/", "display": "standalone"})

@app.get("/sw.js")
async def serve_sw():
    return Response(content="self.addEventListener('install', e => self.skipWaiting()); self.addEventListener('activate', e => clients.claim()); self.addEventListener('fetch', e => e.respondWith(fetch(e.request)));", media_type="application/javascript")

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
        <title>ONYX // NEURAL HUD</title>
        <style>
            :root { --primary: #00f0ff; --secondary: #7000ff; --bg-deep: #02040a; --glass: rgba(0, 240, 255, 0.03); --border-glow: rgba(0, 240, 255, 0.2); --error: #ff0055; }
            * { box-sizing: border-box; }
            body { background-color: var(--bg-deep); background-image: radial-gradient(circle at 50% 50%, #0a1128 0%, #02040a 100%), linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px); background-size: 100% 100%, 30px 30px, 30px 30px; color: var(--primary); font-family: 'Share Tech Mono', monospace; display: flex; flex-direction: column; height: 100vh; margin: 0; justify-content: center; align-items: center; text-align: center; padding: 15px; overflow: hidden; }
            .hud-frame { border: 1px solid var(--border-glow); background: var(--glass); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); padding: 40px 25px; border-radius: 24px; width: 100%; max-width: 480px; box-shadow: 0 0 40px rgba(0, 240, 255, 0.1); position: relative; }
            .pin-input { background: rgba(0, 0, 0, 0.6); border: 1px solid var(--primary); color: var(--primary); font-family: 'Share Tech Mono', monospace; font-size: 1.8rem; padding: 12px; width: 70%; text-align: center; letter-spacing: 12px; margin: 20px 0; border-radius: 8px; outline: none; }
            .error-text { color: var(--error); font-size: 0.9rem; height: 20px; margin-bottom: 10px; }
            .reactor-core { width: 100px; height: 100px; margin: 0 auto 30px auto; position: relative; display: flex; align-items: center; justify-content: center; }
            .ring { position: absolute; border-radius: 50%; border: 2px dashed rgba(0, 240, 255, 0.4); }
            .ring:nth-child(1) { width: 100px; height: 100px; border-color: var(--primary); opacity: 0.2; animation: spin 12s linear infinite; }
            .ring:nth-child(2) { width: 75px; height: 75px; border-color: var(--secondary); animation: spin 8s linear infinite reverse; }
            .ring:nth-child(3) { width: 50px; height: 50px; border-color: var(--primary); animation: spin 4s linear infinite; }
            .core-center { width: 20px; height: 20px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 20px var(--primary); }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            h1 { letter-spacing: 6px; margin: 0 0 5px 0; font-size: 1.8rem; color: #ffffff; }
            .subtitle { font-size: 0.8rem; letter-spacing: 3px; color: rgba(0, 240, 255, 0.7); margin-bottom: 25px; text-transform: uppercase; }
            #status { font-size: 0.9rem; color: #94a3b8; margin-bottom: 20px; min-height: 20px; }
            .terminal-output { margin-top: 15px; font-size: 1.1rem; color: #e2e8f0; min-height: 90px; max-height: 150px; overflow-y: auto; line-height: 1.6; padding: 15px; border-left: 3px solid var(--primary); background: rgba(0, 0, 0, 0.4); text-align: left; border-radius: 0 8px 8px 0; }
            .btn-tactical { background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), rgba(112, 0, 255, 0.1)); color: var(--primary); border: 1px solid var(--primary); padding: 16px 32px; font-size: 1rem; font-family: inherit; font-weight: bold; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; margin-top: 15px; width: 100%; text-transform: uppercase; }
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

            async function authenticate() {
                const code = document.getElementById('pinInput').value;
                document.getElementById('authError').innerText = "Authentification...";
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
                        document.getElementById('authError').innerText = "CODE REJETÉ";
                    }
                } catch (e) {
                    document.getElementById('authError').innerText = "Serveur inaccessible";
                }
            }

            document.getElementById('pinInput').addEventListener('keypress', e => { if (e.key === 'Enter') authenticate(); });

            function initOnyx() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) return alert("Saisie vocale non prise en charge.");

                document.getElementById("startBtn").style.display = "none";
                recognition = new SpeechRecognition();
                recognition.lang = 'fr-FR'; recognition.continuous = true; recognition.interimResults = false;

                recognition.onstart = () => { if(!isProcessing) document.getElementById("status").innerText = "Écoute continue active"; };
                recognition.onresult = async (event) => {
                    const speechText = event.results[event.results.length - 1][0].transcript.trim();
                    if(speechText.length > 1) {
                        document.getElementById("status").innerText = `Traitement: "${speechText}"`;
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
                document.getElementById("response").innerText = "Connexion OpenCode...";
                try {
                    const response = await fetch('/api/interaction', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + jwtToken },
                        body: JSON.stringify({ user_id: "pierre_admin", text_input: text, location: currentCoords })
                    });
                    const data = await response.json();
                    if(response.ok) {
                        document.getElementById("response").innerText = data.reply;
                        speak(data.reply);
                    } else {
                        document.getElementById("response").innerText = data.detail || "Erreur de liaison.";
                        restartListening();
                    }
                } catch (err) {
                    document.getElementById("response").innerText = "ALERTE : Erreur réseau.";
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

                document.getElementById("status").innerText = "Onyx parle...";
                utterance.onend = restartListening;
                utterance.onerror = restartListening;
                window.speechSynthesis.speak(utterance);
            }
            
            function restartListening() {
                isProcessing = false;
                if(isListening) {
                    document.getElementById("status").innerText = "Écoute continue active";
                    try { recognition.start(); } catch(e) {}
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/interaction")
async def handle_interaction(data: UserInteraction, token_data: dict = Depends(verify_token)):
    context_memories = ""
    if memory_client:
        try:
            search_results = memory_client.search(query=data.text_input, filters={'user_id': data.user_id}, limit=3)
            if search_results:
                results_list = search_results.get("results", search_results) if isinstance(search_results, dict) else search_results
                memories = []
                for item in results_list:
                    if isinstance(item, dict) and "memory" in item:
                        memories.append(item["memory"])
                    elif isinstance(item, str):
                        memories.append(item)
                context_memories = "\n".join([f"- {m}" for m in memories])
        except Exception as mem_err:
            logger.error(f"Erreur Mem0 : {mem_err}")

    system_instruction = (
        "Tu es Onyx, l'assistant IA de la Citroën C4 de Pierre. "
        "RÈGLE 1 : Parle EXCLUSIVEMENT en français. "
        "RÈGLE 2 : Ta réponse doit faire MOINS de 20 mots. "
        "Sois concis, direct et factuel.\n\n"
        f"Mémoire sur Pierre :\n{context_memories if context_memories else 'Aucun souvenir.'}"
    )

    user_instruction = f"[Lieu: {data.location}] {data.text_input}"

    reply = await call_opencode_api(system_instruction, user_instruction)

    if memory_client:
        try:
            memory_client.add(messages=[{"role": "user", "content": data.text_input}, {"role": "assistant", "content": reply}], user_id=data.user_id)
        except Exception:
            pass

    return {"status": "success", "reply": reply}
