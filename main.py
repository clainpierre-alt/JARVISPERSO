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

# Page d'accueil HTML intégrée (dispo directement sur ton URL Railway)
@app.get("/", response_class=HTMLResponse)
async def serve_hud():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>JARVIS HUD</title>
        <style>
            body { background-color: #050505; color: #00ffcc; font-family: monospace; display: flex; flex-direction: column; height: 100vh; margin: 0; justify-content: center; align-items: center; text-align: center; padding: 20px; }
            .hud-box { border: 2px solid #00ffcc; padding: 30px; border-radius: 15px; width: 100%; max-width: 400px; box-shadow: 0 0 20px rgba(0,255,204,0.3); }
            button { background: #00ffcc; color: #000; border: none; padding: 15px 30px; font-size: 18px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-top: 20px; width: 100%; }
            #response { margin-top: 25px; font-size: 1.1em; min-height: 60px; line-height: 1.4; }
        </style>
    </head>
    <body>
        <div class="hud-box">
            <h2>J.A.R.V.I.S. HUD</h2>
            <p id="status">Appuie pour parler</p>
            <button onclick="startListening()">🎤 Parler</button>
            <div id="response">...</div>
        </div>
        <script>
            function startListening() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    alert("Reconnaissance vocale non supportée sur ce navigateur.");
                    return;
                }
                const recognition = new SpeechRecognition();
                recognition.lang = 'fr-FR';
                recognition.interimResults = false;
                document.getElementById("status").innerText = "Écoute en cours...";

                recognition.onresult = async function(event) {
                    const speechText = event.results[0][0].transcript;
                    document.getElementById("status").innerText = `Vous: "${speechText}"`;
                    await sendToBackend(speechText);
                };
                recognition.onerror = () => { document.getElementById("status").innerText = "Erreur d'écoute."; };
                recognition.start();
            }

            async function sendToBackend(text) {
                document.getElementById("response").innerText = "Réflexion...";
                try {
                    const response = await fetch('/api/interaction', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: "pierre_admin", text_input: text, location: "Salon-de-Provence" })
                    });
                    const data = await response.json();
                    document.getElementById("response").innerText = data.reply;
                    speak(data.reply);
                    document.getElementById("status").innerText = "Appuie pour parler";
                } catch (err) {
                    document.getElementById("response").innerText = "Erreur serveur.";
                    document.getElementById("status").innerText = "Appuie pour parler";
                }
            }

            function speak(text) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'fr-FR';
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
        "Tu es J.A.R.V.I.S., un assistant embarqué hautement intelligent et concis. "
        "Tu t'adresses à Pierre. Tes réponses doivent faire moins de 20 mots, "
        "être factuelles, et adaptées à un contexte de conduite."
    )
    
    try:
        response = client_ai.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"[Lieu: {data.location}] {data.text_input}",
            config={'system_instruction': system_instruction, 'max_output_tokens': 50}
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
