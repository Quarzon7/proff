from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import uvicorn
import requests

app = FastAPI()

# Abilita CORS per permettere allo smartphone di connettersi al server cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Struttura dati per la richiesta di testo (se non si passa dall'audio)
class TestoRequest(BaseModel):
    testo: str

# Configurazione GROQ (Gratuito)
# Ottieni la chiave gratis su console.groq.com
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def chiama_ai_gratuita(prompt_sistema, prompt_utente):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Chiave GROQ_API_KEY non configurata sul server.")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Utilizziamo Llama 3 (8B o 70B), il modello open-source di Meta, gratuito su Groq
    payload = {
        "model": "llama3-8b-8192", 
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_utente}
        ],
        "temperature": 0.1
    }
    
    response = requests.post(GROQ_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise HTTPException(status_code=response.status_code, detail=f"Errore AI: {response.text}")

@app.post("/v2/processa-audio")
async def processa_audio(file_audio: UploadFile = File(...)):
    try:
        # Nota: Per lo Speech-to-Text gratuito in Cloud, se non vuoi usare Whisper a pagamento,
        # simuliamo la trascrizione iniziale ricevuta dallo smartphone, oppure puoi usare l'API Speech nativa del telefono.
        testo_grezzo_scuola = (
            "Allora cominciamo la seduta della terza B. La professoressa Neri dice che l'alunno "
            "Mario Rossi va male in matematica e ha preso quattro, mentre Luca Bianchi è migliorato tantissimo. "
            "Quindi per Mario Rossi la professoressa Neri propone di attivare subito un piano didattico personalizzato."
        )
        
        # 1. RICONOSCIMENTO AUTOMATICO NOMI (NER) VIA AI GRATUITA
        ner_prompt = (
            "Analizza questo testo scolastico. Identifica tutti i nomi propri di alunni, professori e classi. "
            "Genera un oggetto JSON in cui ogni nome sia associato a una chiave fissa come {{SOGGETTO_A}}, {{SOGGETTO_B}}, {{CLASSE_A}}. "
            "Rispondi SOLO con il JSON puro, senza testo prima o dopo."
        )
        
        risposta_ner = chiama_ai_gratuita(ner_prompt, testo_grezzo_scuola)
        
        # Pulizia della risposta per garantire che sia un JSON valido
        if "```json" in risposta_ner:
            risposta_ner = risposta_ner.split("```json")[1].split("```")[0].strip()
        elif "```" in risposta_ner:
            risposta_ner = risposta_ner.split("```")[1].split("```")[0].strip()
            
        mappa_variabili = json.loads(risposta_ner.strip())
        
        # 2. ANONIMIZZAZIONE SUL SERVER
        testo_anonimizzato = testo_grezzo_scuola
        for token, nome_reale in mappa_variabili.items():
            testo_anonimizzato = testo_anonimizzato.replace(nome_reale, token)

        # 3. MINISTERIALIZZAZIONE IN BUROCRATESE VIA AI GRATUITA
        ministeriale_prompt = (
            "Sei il segretario di un istituto scolastico superiore italiano. Trasforma la traccia anonima "
            "in un estratto di verbale ufficiale usando formule rituali ministeriali e un tono formale. "
            "MANTIENI INTEGRALI I TOKEN DELLE VARIABILI (es. {{SOGGETTO_A}}) senza modificarli o tradurli."
        )
        
        verbale_anonimo_formattato = chiama_ai_gratuita(ministeriale_prompt, testo_anonimizzato)

        return {
            "status": "success",
            "trascrizione_grezza": testo_grezzo_scuola,
            "mappa_variabili": mappa_variabili,
            "verbale_ministeriale_anonimo": verbale_anonimo_formattato
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Configurazione per il cloud (legge la porta assegnata dalla piattaforma)
    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=porta)