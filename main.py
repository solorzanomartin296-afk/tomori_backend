from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests

app = FastAPI()

# Tu llave segura desde Render
API_KEY = os.getenv("GEMINI_API_KEY")

class ChatRequest(BaseModel):
    message: str
    context: str
    image_base64: Optional[str] = None

@app.post("/chat")
async def chat_with_tomori(request: ChatRequest):
    try:
        if not API_KEY:
            raise HTTPException(status_code=500, detail="Falta GEMINI_API_KEY en Render")

        full_prompt = f"{request.context}\n\nPregunta del usuario: {request.message}\nRespuesta de Tomori:"
        
        parts = [{"text": full_prompt}]
        
        # 👇 El bloque corregido con las mayúsculas exactas que exige Google
        if request.image_base64:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": request.image_base64
                }
            })
            
        headers = {"Content-Type": "application/json"}
        
        # Payload 1: Con búsqueda online (si la cuota gratuita lo permite)
        payload_con_busqueda = {
            "contents": [{"parts": parts}],
            "tools": [{"googleSearch": {}}]
        }
        
        # Payload 2: Sin búsqueda online (salva la conexión cuando Google da error 429 en plan gratuito)
        payload_normal = {
            "contents": [{"parts": parts}]
        }
        
        # Lista de modelos: empieza con 3.8 y 3.6, y respalda con los modelos de cuota libre
        modelos = [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash"
        ]
        
        ultimo_error = ""

        for modelo in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={API_KEY}"
            
            # Intento A: Normal (más rápido y sin bloqueo 429 de Grounding gratuito)
            response = requests.post(url, json=payload_normal, headers=headers)
            
            # Si quieres que intente con búsqueda primero en caso de que el normal falle:
            if response.status_code != 200:
                response_search = requests.post(url, json=payload_con_busqueda, headers=headers)
                if response_search.status_code == 200:
                    response = response_search

            if response.status_code == 200:
                data = response.json()
                reply = data['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ RESPUESTA EXITOSA CON: {modelo}")
                return {"reply": reply}
            else:
                ultimo_error = f"[{modelo} -> Código {response.status_code}]: {response.text}"
                print(f"⚠️ Saltando {modelo} (Código {response.status_code})")
                
        print(f"🚨 ERROR DE GOOGLE EN TODOS LOS MODELOS: {ultimo_error}")
        raise HTTPException(status_code=500, detail=f"Gemini rechazó la conexión: {ultimo_error}")
            
    except Exception as e:
        print(f"🚨 ERROR DEL SERVIDOR: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))
