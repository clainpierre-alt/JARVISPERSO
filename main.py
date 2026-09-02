import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from supabase import create_client, Client

app = FastAPI(title="JARVIS Car Assistant Backend (Gemini)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation des clients
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Client Gemini officiel
client_ai = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

class UserInteraction(BaseModel):
    user_id: str
    text_input: str
    location: str = "Inconnu"

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
        # Appel à Gemini (gemini-2.5-flash est idéal pour la latence)
        response = client_ai.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"[Lieu: {data.location}] {data.text_input}",
            config={
                'system_instruction': system_instruction,
                'max_output_tokens': 50,
            }
        )
        reply = response.text

        # Sauvegarde dans Supabase pour l'historique
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
