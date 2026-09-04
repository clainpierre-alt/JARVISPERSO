import os
import logging
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from mem0 import MemoryClient

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ONYX_CORE")

# 1. Initialize the FastAPI Application First
app = FastAPI(title="ONYX // Full Autonomous HUD")

# 2. Add Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Environment & Clients Configuration
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")
ACCESS_CODE = os.getenv("ACCESS_CODE", "0000")

client_ai = OpenAI(
    api_key=OPENCODE_API_KEY,
    base_url="https://api.opencode.ai/v1" 
) if OPENCODE_API_KEY else None

memory_client = MemoryClient(api_key=MEM0_API_KEY) if MEM0_API_KEY else None

# 4. Pydantic Models
class UserInteraction(BaseModel):
    user_id: str
    text_input: str
    location: str = "Inconnu"

class AuthRequest(BaseModel):
    code: str

# 5. Application Routes
@app.post("/api/auth")
async def verify_auth(req: AuthRequest):
    if req.code == ACCESS_CODE:
        logger.info("Authentification réussie pour un terminal HUD.")
        return {"status": "success"}
    logger.warning(f"Tentative d'accès refusée (code: {req.code})")
    raise HTTPException(status_code=401, detail="Code d'accès invalide")

@app.get("/", response_class=HTMLResponse)
async def serve_hud():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>ONYX // HOLOGRAPHIC HUD</title>
        <style>
            :root {
                --primary: #00f0ff;
                --secondary: #7000ff;
                --bg-deep: #02040a;
                --glass: rgba(0, 240, 255, 0.03);
                --border-glow: rgba(0, 240, 255, 0.2);
                --error: #ff0055;
            }
            body {
                background-color: var(--bg-deep);
                background-image: 
                    radial-gradient(circle at 50% 50%, #0a1128 0%, #02040a 100%),
                    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
                background-size: 100% 100%, 30px 30px, 30px 30px;
                color: var(--primary);
                font-family: 'Share Tech Mono', 'Courier New', monospace;
                display: flex;
                flex-direction: column;
                height: 100vh;
                margin: 0;
                justify-content: center;
                align-items: center;
                text-align: center;
                padding: 15px;
                overflow: hidden;
            }
            .hud-frame {
                border: 1px solid var(--border-glow);
                background: var(--glass);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                padding: 35px 25px;
                border-radius: 24px;
                width: 100%;
                max-width: 480px;
                box-shadow: 0 0 40px rgba(0, 240, 255, 0.1), inset 0 0 20px rgba(0, 240, 255, 0.05);
                position: relative;
            }
            .hud-frame::before, .hud-frame::after { content: ''; position: absolute; width: 15px; height: 15px; border-color: var(--primary); border-style: solid; }
            .hud-frame::before { top: -1px; left: -1px; border-width: 2px 0 0 2px; }
            .hud-frame::after { bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }
            
            .pin-input {
                background: rgba(0, 0, 0, 0.5); border: 1px solid var(--primary); color: var(--primary);
                font-family: 'Share Tech Mono', monospace; font-size: 1.5rem; padding: 10px; width: 60%;
                text-align: center; letter-spacing: 10px; margin: 20px 0; border-radius: 8px; outline: none;
            }
            .pin-input:focus { box-shadow: 0 0 15px var(--primary); }
            .error-text { color: var(--error); font-size: 0.85rem; height: 20px; margin-bottom: 10px; }

            .reactor-core { width: 90px; height: 90px; margin: 0 auto 25px auto; position: relative; display: flex; align-items: center; justify-content: center; }
            .ring { position: absolute; border-radius: 50%; border: 2px dashed rgba(0, 240, 255, 0.4); animation: spin 10s linear infinite; }
            .ring:nth-child(1) { width: 90px; height: 90px; border-color: var(--primary); border-width: 1px; border-style: solid; opacity: 0.3; }
            .ring:nth-child(2) { width: 70px; height: 70px; border-color: var(--secondary); animation-direction: reverse; animation-duration: 6s; }
            .ring:nth-child(3) { width: 50px; height: 50px; border-color: var(--primary); animation-duration: 4s; }
            .core-center { width: 20px; height: 20px; background: var(--primary); border-radius: 50%; box-shadow: 0 0 20px var(--primary), 0 0 40px var(--secondary); animation: pulse-core 2s ease-in-out infinite; }
            
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            @keyframes pulse-core { 0%, 100% { transform: scale(0.8); opacity: 0.7; } 50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 30px var(--primary), 0 0 60px var(--secondary); } }
            
            h1 { letter-spacing: 5px; margin: 0 0 5px 0; font-size: 1.5rem; color: #ffffff; text-shadow: 0 0 10px rgba(0, 240, 255, 0.6); }
            .subtitle { font-size: 0.75rem; letter-spacing: 2px; color: rgba(0, 240, 255, 0.6); margin-bottom: 20px; text-transform: uppercase; }
            #status { font-size: 0.85rem; color: #94a3b8; margin-bottom: 25px; min-height: 20px; letter-spacing: 1px; }
            .terminal-output { margin-top: 15px; font-size: 1.05rem; color: #e2e8f0; min-height: 90px; max-height: 140px; overflow-y: auto; line-height: 1.6; padding: 15px; border-left: 2px solid var(--primary); background: rgba(0, 0, 0, 0.3); text-align: left; border-radius: 0 8px 8px 0; }
            
            .btn-tactical {
                background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), rgba(112, 0, 255, 0.1));
                color: var(--primary); border: 1px solid var(--primary); padding: 14px 28px; font-size: 0.95rem; font-family: inherit; font-weight: bold; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; margin-top: 10px; letter-spacing: 2px; width: 100%; text-transform: uppercase;
            }
            .btn-tactical:hover { background: var(--primary); color: var(--bg-deep); box-shadow: 0 0 25px var(--primary); }
            .active-pulse { border-color: var(--primary) !important; box-shadow: 0 0 30px rgba(0, 240, 255, 0.4) !important; }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
    </head>
    <body>

        <div class="hud-frame" id="lockScreen">
            <h1>ONYX PROTOCOL</h1>
            <div class="subtitle">Identification Requise</div>
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
            <div id="status">Système en veille - Prêt</div>
            <button class="btn-tactical" id="startBtn" onclick="initOnyx()">ACTIVER LA LIAISON</button>
            <div class="terminal-output" id="response">En attente de paramètres...</div>
        </div>

        <script>
            let recognition;
            let isListening = false;
            let currentCoords = "Inconnu";
            let sessionToken = "";

            async function authenticate() {
                const code = document.getElementById('pinInput').value;
                document.getElementById('authError').innerText = "Vérification...";
                
                try {
                    const res = await fetch('/api/auth', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code: code })
                    });
                    
                    if (res.ok) {
                        sessionToken = code; 
                        document.getElementById('lockScreen').style.display = 'none';
                        document.getElementById('hudFrame').style.display = 'block';
                    } else {
                        document.getElementById('authError').innerText = "ACCÈS REFUSÉ";
                        document.getElementById('pinInput').value = "";
                    }
                } catch (e) {
                    document.getElementById('authError').innerText = "Erreur de connexion serveur";
                }
            }

            document.getElementById('pinInput').addEventListener('keypress', function (e) {
                if (e.key === 'Enter') authenticate();
            });

            function trackLocation() {
                if (navigator.geolocation) {
                    navigator.geolocation.watchPosition(
                        (position) => { currentCoords = `${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}`; },
                        (error) => { console.warn("GPS non dispo."); },
                        { enableHighAccuracy: true }
                    );
                }
            }

            function initOnyx() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert("Module vocal non compatible.");
                    return;
                }

                trackLocation();
                document.getElementById("startBtn").style.display = "none";
                document.getElementById("status").innerText = "Écoute continue active (Mains Libres)";
                document.getElementById("hudFrame").classList.add("active-pulse");

                recognition = new SpeechRecognition();
                recognition.lang = 'fr-FR';
                recognition.continuous = true;
                recognition.interimResults = false;

                recognition.onresult = async function(event) {
                    const speechText = event.results[event.results.length - 1][0].transcript.trim();
                    document.getElementById("status").innerText = `Reçu : "${speechText}"`;
                    await sendToBackend(speechText);
                };

                recognition.onend = function() {
                    if (isListening) {
                        try { recognition.start(); } catch (e) {}
                    }
                };

                isListening = true;
                try { recognition.start(); } catch(e) {}
            }

            async function sendToBackend(text) {
                document.getElementById("response").innerText = "Analyse neurale Onyx...";
                try {
                    const response = await fetch('/api/interaction', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-Access-Code': sessionToken 
                        },
                        body: JSON.stringify({ 
                            user_id: "pierre_admin", 
                            text_input: text, 
                            location: currentCoords 
                        })
                    });
                    
                    if (response.status === 401) {
                        document.getElementById("response").innerText = "ALERTE : Session expirée ou invalide.";
                        return;
                    }
                    if (!response.ok) throw new Error(`Erreur réseau: HTTP ${response.status}`);

                    const data = await response.json();
                    document.getElementById("response").innerText = data.reply;
                    speak(data.reply);
                } catch (err) {
                    document.getElementById("response").innerText = "ALERTE : Perte de liaison serveur. Vérifiez la connexion.";
                    console.error("Fetch error:", err);
                }
            }

            function speak(text) {
                if (!('speechSynthesis' in window)) return;
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'fr-FR';
                utterance.rate = 1.05;
                
                utterance.onend = () => {
                    document.getElementById("status").innerText = "Écoute continue active (Mains Libres)";
                };
                window.speechSynthesis.speak(utterance);
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/interaction")
async def handle_interaction(data: UserInteraction, x_access_code: str = Header(None)):
    if x_access_code != ACCESS_CODE:
        logger.warning(f"Refus API Vocal - Code invalide: {x_access_code}")
        raise HTTPException(status_code=401, detail="Non autorisé")

    if not client_ai:
        logger.error("La clé OPENCODE_API_KEY est introuvable.")
        raise HTTPException(status_code=500, detail="OpenCode API Key non configurée")
    
    logger.info(f"Requête reçue de {data.user_id} depuis {data.location} : '{data.text_input}'")

    try:
        context_memories = ""
        if memory_client:
            try:
                search_results = memory_client.search(
                    query=data.text_input, 
                    filters={'user_id': data.user_id}, 
                    limit=3
                )
                if search_results:
                    memories_list = [f"- {res['memory']}" for res in search_results]
                    context_memories = "\n".join(memories_list)
                    logger.info(f"Mem0 a trouvé {len(search_results)} souvenirs.")
            except Exception as mem_err:
                logger.error(f"Échec de la recherche Mem0 : {mem_err}")

        system_instruction = (
            "Tu es Onyx, un assistant embarqué de Citroën C4, intelligent, concis et factuel. "
            "Tu t'adresses à Pierre. Tes réponses doivent impérativement faire moins de 20 mots, "
            "être formulées de manière directe, et être adaptées à un contexte de conduite automobile.\n\n"
            f"Faits et souvenirs pertinents sur Pierre :\n{context_memories if context_memories else 'Aucun souvenir.'}"
        )

        logger.info("Envoi de la requête au modèle LLM...")
        completion = client_ai.chat.completions.create(
            model="GPT 5.4 Nano", 
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"[Lieu: {data.location}] {data.text_input}"}
            ],
            max_tokens=60,
            temperature=0.3
        )
        
        if isinstance(completion, str):
            reply = completion.strip()
        elif hasattr(completion, 'choices') and completion.choices:
            reply = completion.choices[0].message.content.strip()
        else:
            reply = "Je n'ai pas de réponse."
            
        logger.info(f"Onyx répond : '{reply}'")

        if memory_client:
            try:
                memory_client.add(
                    messages=[
                        {"role": "user", "content": data.text_input},
                        {"role": "assistant", "content": reply}
                    ],
                    user_id=data.user_id
                )
                logger.info("Interaction sauvegardée dans Mem0.")
            except Exception as mem_err:
                logger.error(f"Échec sauvegarde Mem0 : {mem_err}")

        score = 5 if len(reply.split()) <= 25 else 3
        return {"status": "success", "reply": reply, "auto_score": score}
        
    except Exception as e:
        logger.error(f"Erreur critique backend : {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
