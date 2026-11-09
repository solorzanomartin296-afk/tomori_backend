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

# 🔔 Sin 'async' para que FastAPI maneje hilos paralelos y no congele el servidor
@app.get("/ping")
def ping_server():
    return {"status": "awake", "message": "Tomori está despierta y lista"}

@app.post("/chat")
def chat_with_tomori(request: ChatRequest):
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
        
        # ⚡ Lista priorizada
        modelos = [
            "gemini-3.8-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]
        
        ultimo_error = ""

        for modelo in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={API_KEY}"
            try:
                # ⏱️ Timeout de 5s para conectar y 12s para leer: si un modelo se cuelga, salta rápido al siguiente
                response = requests.post(url, json=payload, headers=headers, timeout=(5, 12))

                if response.status_code == 200:
                    data = response.json()
                    reply = data['candidates'][0]['content']['parts'][0]['text']
                    print(f"⚡ RESPUESTA RÁPIDA CON: {modelo}")
                    return {"reply": reply}
                else:
                    ultimo_error = f"[{modelo} -> {response.status_code}]"
                    print(f"⚠️ Saltando {modelo} (Código {response.status_code})")
            except requests.exceptions.Timeout:
                ultimo_error = f"[{modelo} -> Timeout]"
                print(f"⏱️ {modelo} tardó demasiado, saltando al siguiente modelo...")
                continue
                
        raise HTTPException(status_code=500, detail=f"Rechazo: {ultimo_error}")
            
    except Exception as e:
        print(f"🚨 ERROR DEL SERVIDOR: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))
