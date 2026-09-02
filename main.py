import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from supabase import create_client, Client

app = FastAPI(title="J.A.R.V.I.S. // Full Autonomous HUD")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client_ai = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

class UserInteraction(BaseModel):
    user_id: str
    text_input: str
    location: str = "Inconnu"

# Interface HUD Holographique avec Géolocalisation Temps Réel et Écoute Continue
@app.get("/", response_class=HTMLResponse)
async def serve_hud():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>J.A.R.V.I.S. // HOLOGRAPHIC HUD</title>
        <style>
            :root {
                --primary: #00f0ff;
                --secondary: #7000ff;
                --bg-deep: #02040a;
                --glass: rgba(0, 240, 255, 0.03);
                --border-glow: rgba(0, 240, 255, 0.2);
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

            .hud-frame::before, .hud-frame::after {
                content: '';
                position: absolute;
                width: 15px;
                height: 15px;
                border-color: var(--primary);
                border-style: solid;
            }
            .hud-frame::before { top: -1px; left: -1px; border-width: 2px 0 0 2px; }
            .hud-frame::after { bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }

            .reactor-core {
                width: 90px;
                height: 90px;
                margin: 0 auto 25px auto;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .ring {
                position: absolute;
                border-radius: 50%;
                border: 2px dashed rgba(0, 240, 255, 0.4);
                animation: spin 10s linear infinite;
            }

            .ring:nth-child(1) { width: 90px; height: 90px; border-color: var(--primary); border-width: 1px; border-style: solid; opacity: 0.3; }
            .ring:nth-child(2) { width: 70px; height: 70px; border-color: var(--secondary); animation-direction: reverse; animation-duration: 6s; }
            .ring:nth-child(3) { width: 50px; height: 50px; border-color: var(--primary); animation-duration: 4s; }

            .core-center {
                width: 20px;
                height: 20px;
                background: var(--primary);
                border-radius: 50%;
                box-shadow: 0 0 20px var(--primary), 0 0 40px var(--secondary);
                animation: pulse-core 2s ease-in-out infinite;
            }

            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            @keyframes pulse-core {
                0%, 100% { transform: scale(0.8); opacity: 0.7; }
                50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 30px var(--primary), 0 0 60px var(--secondary); }
            }

            h1 {
                letter-spacing: 5px;
                margin: 0 0 5px 0;
                font-size: 1.5rem;
                color: #ffffff;
                text-shadow: 0 0 10px rgba(0, 240, 255, 0.6);
            }

            .subtitle {
                font-size: 0.75rem;
                letter-spacing: 2px;
                color: rgba(0, 240, 255, 0.6);
                margin-bottom: 20px;
                text-transform: uppercase;
            }

            #status {
                font-size: 0.85rem;
                color: #94a3b8;
                margin-bottom: 25px;
                min-height: 20px;
                letter-spacing: 1px;
            }

            .terminal-output {
                margin-top: 15px;
                font-size: 1.05rem;
                color: #e2e8f0;
                min-height: 90px;
                max-height: 140px;
                overflow-y: auto;
                line-height: 1.6;
                padding: 15px;
                border-left: 2px solid var(--primary);
                background: rgba(0, 0, 0, 0.3);
                text-align: left;
                border-radius: 0 8px 8px 0;
            }

            .btn-tactical {
                background: linear-gradient(135deg, rgba(0, 240, 255, 0.1), rgba(112, 0, 255, 0.1));
                color: var(--primary);
                border: 1px solid var(--primary);
                padding: 14px 28px;
                font-size: 0.95rem;
                font-family: inherit;
                font-weight: bold;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
                letter-spacing: 2px;
                width: 100%;
                text-transform: uppercase;
            }

            .btn-tactical:hover {
                background: var(--primary);
                color: var(--bg-deep);
                box-shadow: 0 0 25px var(--primary);
            }

            .active-pulse {
                border-color: var(--primary) !important;
                box-shadow: 0 0 30px rgba(0, 240, 255, 0.4) !important;
            }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="hud-frame" id="hudFrame">
            <div class="reactor-core">
                <div class="ring"></div>
                <div class="ring"></div>
                <div class="ring"></div>
                <div class="core-center"></div>
            </div>
            
            <h1>J.A.R.V.I.S.</h1>
            <div class="subtitle">Autonomous Vehicular Intelligence</div>
            
            <div id="status">Système en veille - Prêt</div>
            
            <button class="btn-tactical" id="startBtn" onclick="initJarvis()">ACTIVER LA LIAISON</button>
            
            <div class="terminal-output" id="response">En attente de paramètres...</div>
        </div>

        <script>
            let recognition;
            let isListening = false;
            let currentCoords = "Salon-de-Provence";

            // Récupération dynamique du GPS du téléphone/voiture en arrière-plan
            function trackLocation() {
                if (navigator.geolocation) {
                    navigator.geolocation.watchPosition(
                        (position) => {
                            currentCoords = `${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}`;
                        },
                        (error) => { console.warn("GPS non dispo, mode par défaut."); },
                        { enableHighAccuracy: true }
                    );
                }
            }

            function initJarvis() {
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
                document.getElementById("response").innerText = "Analyse neurale & mémoire...";
                try {
                    const response = await fetch('/api/interaction', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            user_id: "pierre_admin", 
                            text_input: text, 
                            location: currentCoords 
                        })
                    });
                    
                    if (!response.ok) throw new Error("Erreur réseau");

                    const data = await response.json();
                    document.getElementById("response").innerText = data.reply;
                    speak(data.reply);
                } catch (err) {
                    document.getElementById("response").innerText = "ALERTE : Perte de liaison serveur.";
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
async def handle_interaction(data: UserInteraction):
    if not client_ai:
        raise HTTPException(status_code=500, detail="Gemini API Key non configurée")

    try:
        # 1. Génération de l'embedding de la requête utilisateur (pour la mémoire RAG)
        embedding_response = client_ai.models.embed_content(
            model="text-embedding-004",
            contents=data.text_input
        )
        query_embedding = embedding_response.embedding.values

        # 2. Recherche des souvenirs passés similaires dans Supabase via pgvector
        context_memories = ""
        if supabase:
            try:
                rpc_result = supabase.rpc("match_interactions", {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.70,
                    "match_count": 3
                }).execute()
                
                if rpc_result.data:
                    memories_list = [f"- Ancien échange : User: '{row['input_text']}' -> Toi: '{row['output_text']}'" for row in rpc_result.data]
                    context_memories = "\n".join(memories_list)
            except Exception as vector_err:
                print(f"Info recherche vectorielle : {vector_err}")

        # 3. Instruction système enrichie avec la mémoire long-terme
        system_instruction = (
            "Tu es J.A.R.V.I.S., un assistant embarqué hautement intelligent, concis et factuel. "
            "Tu t'adresses à Pierre. Tes réponses doivent impérativement faire moins de 20 mots, "
            "être formulées de manière directe, et être adaptées à un contexte de conduite automobile.\n\n"
            f"Contexte mémoriel pertinent issu des interactions passées de Pierre :\n{context_memories if context_memories else 'Aucun souvenir direct similaire.'}"
        )

        # 4. Génération de la réponse via le modèle Gemini
        chat = client_ai.chats.create(
            model='gemini-2.5-flash',
            config={
                'system_instruction': system_instruction,
                'max_output_tokens': 40
            }
        )
        
        response = chat.send_message(f"[Coordonnées GPS/Lieu: {data.location}] {data.text_input}")
        reply = response.text if response and response.text else "Je n'ai pas de réponse."

        # 5. Scoring automatique de la concision
        score = 5 if len(reply.split()) <= 25 else 3

        # 6. Sauvegarde de l'interaction et de son embedding dans Supabase
        if supabase:
            try:
                supabase.table("interactions_log").insert({
                    "user_id": data.user_id,
                    "input_text": data.text_input,
                    "output_text": reply,
                    "location": data.location,
                    "score": score,
                    "embedding": query_embedding
                }).execute()
            except Exception as db_err:
                print(f"Erreur insertion Supabase avec embedding : {db_err}")

        return {"status": "success", "reply": reply, "auto_score": score}
        
    except Exception as e:
        print(f"Erreur critique backend : {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
