from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests

app = FastAPI()

API_KEY = os.getenv("GEMINI_API_KEY")

# Guardamos en memoria el modelo ganador para que a partir del 2do mensaje responda en 1 segundo
MODELO_ACTIVO = None

class ChatRequest(BaseModel):
    message: str
    context: str
    image_base64: Optional[str] = None

@app.get("/ping")
def ping_server():
    return {"status": "awake", "message": "Tomori está despierta y lista"}

def obtener_modelos_disponibles():
    """Pregunta directamente a Google qué modelos tiene permitidos esta API Key"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            modelos_validos = []
            for m in data.get("models", []):
                metodos = m.get("supportedGenerationMethods", [])
                nombre = m.get("name", "").replace("models/", "")
                if "generateContent" in metodos and "gemini" in nombre and "vision" not in nombre:
                    modelos_validos.append(nombre)
            # Priorizamos los que digan 'flash' o 'lite' porque tienen más cuota gratuita y son más rápidos
            modelos_validos.sort(key=lambda x: (0 if "flash" in x else 1, 0 if "lite" in x else 1))
            print(f"📋 MODELOS DETECTADOS EN TU CUENTA: {modelos_validos}")
            return modelos_validos
    except Exception as e:
        print(f"⚠️ No se pudo listar modelos: {e}")
    return ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-flash-latest"]

@app.post("/chat")
def chat_with_tomori(request: ChatRequest):
    global MODELO_ACTIVO
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
        payload = {"contents": [{"parts": parts}]}
        
        # Armamos la lista poniendo de primero el modelo que ya sabemos que funciona
        modelos_a_probar = []
        if MODELO_ACTIVO:
            modelos_a_probar.append(MODELO_ACTIVO)
            
        for m in obtener_modelos_disponibles():
            if m not in modelos_a_probar:
                modelos_a_probar.append(m)

        errores_resumen = []

        for modelo in modelos_a_probar:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={API_KEY}"
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=(5, 15))

                if response.status_code == 200:
                    data = response.json()
                    reply = data['candidates'][0]['content']['parts'][0]['text']
                    MODELO_ACTIVO = modelo  # 🧠 Lo memoriza para que el próximo mensaje sea instantáneo
                    print(f"⚡ RESPUESTA EXITOSA CON: {modelo}")
                    return {"reply": reply}
                else:
                    errores_resumen.append(f"{modelo}:{response.status_code}")
                    print(f"⚠️ Saltando {modelo} (Código {response.status_code})")
            except requests.exceptions.Timeout:
                errores_resumen.append(f"{modelo}:Timeout")
                continue
                
        raise HTTPException(status_code=500, detail=f"Rechazo en todos: {', '.join(errores_resumen[:5])}")
            
    except Exception as e:
        print(f"🚨 ERROR DEL SERVIDOR: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))
