import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from supabase import create_client, Client

app = FastAPI(title="JARVIS Car Assistant")

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

# Page d'accueil HUD intégrée avec écoute continue et design futuriste
@app.get("/", response_class=HTMLResponse)
async def serve_hud():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>J.A.R.V.I.S. HUD</title>
        <style>
            body {
                background-color: #030712;
                color: #00ffcc;
                font-family: 'Courier New', Courier, monospace;
                display: flex;
                flex-direction: column;
                height: 100vh;
                margin: 0;
                justify-content: center;
                align-items: center;
                text-align: center;
                padding: 20px;
                overflow: hidden;
            }
            .hud-container {
                border: 1px solid rgba(0, 255, 204, 0.3);
                background: rgba(3, 7, 18, 0.8);
                padding: 40px;
                border-radius: 20px;
                width: 100%;
                max-width: 450px;
                box-shadow: 0 0 30px rgba(0, 255, 204, 0.15);
                position: relative;
            }
            .core-glow {
                width: 80px;
                height: 80px;
                background: radial-gradient(circle, rgba(0,255,204,0.8) 0%, rgba(3,7,18,0) 70%);
                border-radius: 50%;
                margin: 0 auto 25px auto;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(0.95); opacity: 0.6; }
                50% { transform: scale(1.15); opacity: 1; shadow: 0 0 20px #00ffcc; }
                100% { transform: scale(0.95); opacity: 0.6; }
            }
            h2 {
                letter-spacing: 3px;
                margin-bottom: 10px;
                font-size: 1.4rem;
                color: #fff;
                text-shadow: 0 0 10px rgba(0,255,204,0.5);
            }
            #status {
                font-size: 0.9rem;
                color: #94a3b8;
                margin-bottom: 20px;
                min-height: 24px;
            }
            #response {
                margin-top: 20px;
                font-size: 1.15rem;
                color: #00ffcc;
                min-height: 80px;
                line-height: 1.5;
                padding: 10px;
                border-left: 2px solid #00ffcc;
                background: rgba(0, 255, 204, 0.03);
                text-align: left;
            }
            .btn-activate {
                background: transparent;
                color: #00ffcc;
                border: 1px solid #00ffcc;
                padding: 12px 24px;
                font-size: 1rem;
                font-family: inherit;
                font-weight: bold;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 15px;
                letter-spacing: 1px;
            }
            .btn-activate:hover {
                background: #00ffcc;
                color: #030712;
                box-shadow: 0 0 15px rgba(0,255,204,0.5);
            }
        </style>
    </head>
    <body>
        <div class="hud-container">
            <div class="core-glow"></div>
            <h2>J.A.R.V.I.S.</h2>
            <div id="status">Système en veille - Cliquez pour activer</div>
            <button class="btn-activate" id="startBtn" onclick="initJarvis()">ACTIVER L'ÉCOUTE</button>
            <div id="response" id="output">En attente de commande...</div>
        </div>

        <script>
            let recognition;
            let isListening = false;

            function initJarvis() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert("La reconnaissance vocale n'est pas supportée par ce navigateur.");
                    return;
                }

                // Masquer le bouton d'activation initiale une fois lancé
                document.getElementById("startBtn").style.display = "none";
                document.getElementById("status").innerText = "Écoute continue active...";

                recognition = new SpeechRecognition();
                recognition.lang = 'fr-FR';
                recognition.continuous = true;
                recognition.interimResults = false;

                recognition.onresult = async function(event) {
                    const speechText = event.results[event.results.length - 1][0].transcript.trim();
                    document.getElementById("status").innerText = `Entendu : "${speechText}"`;
                    await sendToBackend(speechText);
                };

                recognition.onerror = function(event) {
                    console.warn("Erreur micro:", event.error);
                };

                recognition.onend = function() {
                    // Relance automatique pour maintenir l'écoute permanente
                    if (isListening) {
                        try {
                            recognition.start();
                        } catch (e) {
                            console.log("Re-démarrage ignoré ou déjà en cours");
                        }
                    }
                };

                isListening = true;
                try {
                    recognition.start();
                } catch(e) {
                    console.error(e);
                }
            }

            async function sendToBackend(text) {
                document.getElementById("response").innerText = "Analyse en cours...";
                try {
                    const response = await fetch('/api/interaction', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            user_id: "pierre_admin", 
                            text_input: text, 
                            location: "Salon-de-Provence" 
                        })
                    });
                    
                    if (!response.ok) throw new Error("Erreur réseau");

                    const data = await response.json();
                    document.getElementById("response").innerText = data.reply;
                    speak(data.reply);
                } catch (err) {
                    document.getElementById("response").innerText = "Erreur de communication avec le serveur.";
                }
            }

            function speak(text) {
                if (!('speechSynthesis' in window)) return;
                window.speechSynthesis.cancel(); // Coupe la parole précédente si besoin
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'fr-FR';
                utterance.rate = 1.05;
                
                utterance.onend = () => {
                    document.getElementById("status").innerText = "Écoute continue active...";
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

    system_instruction = (
        "Tu es J.A.R.V.I.S., un assistant embarqué hautement intelligent, concis et factuel. "
        "Tu t'adresses à Pierre. Tes réponses doivent impérativement faire moins de 20 mots, "
        "être formulées de manière directe, et être adaptées à un contexte de conduite automobile."
    )
    
    try:
        response = client_ai.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"[Lieu: {data.location}] {data.text_input}",
            config={'system_instruction': system_instruction, 'max_output_tokens': 40}
        )
        reply = response.text

        if supabase:
            supabase.table("interactions_log").insert({
                "user_id": data.user_id,
                "input_text": data.text_input,
                "output_text": reply,
                "location": data.location
            }).execute()

        return {"status": "success", "reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
