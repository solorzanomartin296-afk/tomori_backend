from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests

app = FastAPI()

API_KEY = os.getenv("GEMINI_API_KEY")

class ChatRequest(BaseModel):
    message: str
    context: str
    image_base64: Optional[str] = None

# 🔔 Ruta ligera para que Flutter despierte a Render en silencio
@app.get("/ping")
async def ping_server():
    return {"status": "awake", "message": "Tomori está despierta y lista"}

@app.post("/chat")
async def chat_with_tomori(request: ChatRequest):
    try:
        if not API_KEY:
            raise HTTPException(status_code=500, detail="Falta GEMINI_API_KEY en Render")

        full_prompt = f"{request.context}\n\nPregunta del usuario: {request.message}\nRespuesta de Tomori:"
        parts = [{"text": full_prompt}]
        
        if request.image_base64:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": request.image_base64
                }
            })
            
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": parts}]
        }
        
        # ⚡ gemini-3.8-flash en PRIMER lugar para respuesta inmediata
        modelos = [
            "gemini-3.8-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-3.6-flash"
        ]
        
        ultimo_error = ""

        for modelo in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={API_KEY}"
            response = requests.post(url, json=payload, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                reply = data['candidates'][0]['content']['parts'][0]['text']
                print(f"⚡ RESPUESTA RÁPIDA CON: {modelo}")
                return {"reply": reply}
            else:
                ultimo_error = f"[{modelo} -> {response.status_code}]"
                print(f"⚠️ Saltando {modelo} ({response.status_code})")
                
        raise HTTPException(status_code=500, detail=f"Rechazo: {ultimo_error}")
            
    except Exception as e:
        print(f"🚨 ERROR DEL SERVIDOR: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))
