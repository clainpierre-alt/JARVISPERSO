import os
import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from supabase import create_client, Client

app = FastAPI(title="JARVIS Car Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation des clients (récupérés depuis les variables d'environnement de Railway)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

openai.api_key = OPENAI_API_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

class UserInteraction(BaseModel):
    user_id: str
    text_input: str
    location: str = "Inconnu"

@app.post("/api/interaction")
async def handle_interaction(data: UserInteraction):
    """Gère le traitement textuel, le contexte et la mémoire long-terme"""
    system_prompt = (
        "Tu es J.A.R.V.I.S., un assistant embarqué hautement intelligent et concis. "
        "Tu t'adresses à Pierre. Tes réponses doivent faire moins de 20 mots, "
        "être factuelles, et adaptées à un contexte de conduite."
    )
    
    try:
        # Appel au LLM (GPT-4o mini par exemple pour la rapidité)
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"[Lieu: {data.location}] {data.text_input}"}
            ],
            max_tokens=50
        )
        reply = response.choices[0].message.content

        # Sauvegarde dans Supabase si configuré (Apprentissage continu / Historique)
        if supabase:
            supabase.table("interactions_log").insert({
                "user_id": data.user_id,
                "input_text": data.text_input,
                "output_text": reply,
                "location": data.location
            }).execute()

        return {"status": "success", "reply": reply}
    
    - Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Canal temps réel pour le GPS et la détection d'ambiance / passagers"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # Exemple de données reçues du téléphone : {"lat": 43.6, "lon": 5.2, "speed": 50, "passengers": ["Sarah"]}
            
            # Logique proactive J.A.R.V.I.S. (Ex: Alerte météo ou habitude)
            action_triggered = None
            if data.get("speed", 0) > 130:
                action_triggered = "Attention Pierre, ta vitesse dépasse les limites autorisées."
            
            await websocket.send_json({
                "status": "received", 
                "proactive_message": action_triggered
            })
    except WebSocketDisconnect:
        print("Téléphone déconnecté du flux WebSocket")
