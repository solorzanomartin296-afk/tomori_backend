from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests

app = FastAPI()

# Tu llave y el modelo 3.6 de Google
API_KEY = os.getenv("GEMINI_API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={API_KEY}"

class ChatRequest(BaseModel):
    message: str
    context: str
    image_base64: Optional[str] = None

@app.post("/chat")
async def chat_with_tomori(request: ChatRequest):
    try:
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
            
        payload = {
            "contents": [{"parts": parts}],
            "tools": [{"googleSearch": {}}] # 🌍 CEREBRO ONLINE ACTIVADO
        }
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            reply = data['candidates'][0]['content']['parts'][0]['text']
            return {"reply": reply}
        else:
            print(f"🚨 ERROR DE GOOGLE: {response.text}")
            raise HTTPException(status_code=500, detail="Gemini rechazó la conexión")
            
    except Exception as e:
        print(f"🚨 ERROR DEL SERVIDOR: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))