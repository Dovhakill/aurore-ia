# Dans src/aurore/summarize.py

from typing import Sequence
import requests
from bs4 import BeautifulSoup
import json
from google.generativeai import Client
# MODIFICATION 1 : On importe GenerationConfig au lieu de ResponseParams
from google.generativeai.types import GenerationConfig
from .config import Settings

def fetch_text(url: str) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": Settings.USER_AGENT}, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(s.strip() for s in soup.get_text(" ").split())
        return text
    except Exception:
        return ""

def synthesize_neutral(topic: str, sources: Sequence[str]) -> dict:
    client = Client(api_key=Settings.GEMINI_API_KEY)

    prompt = f"""
Tu es un journaliste factuel qui écrit en français.
Fusionne les informations des trois sources en un article neutre et clair.
Répond EXCLUSIVEMENT en JSON valide au format suivant :

{{
  "title": "Titre court et précis",
  "dek": "Chapeau introductif de 1-2 phrases",
  "body": "<p>HTML structuré de l'article</p>",
  "bullets": ["Point clé 1", "Point clé 2", "Point clé 3"],
  "meta": {{
    "keywords": ["mot", "clé"],
    "description": "Phrase descriptive optimisée SEO"
  }}
}}

Sujet : {topic}

Sources :
1. {sources[0]}
2. {sources[1]}
3. {sources[2]}

Utilise le contenu fourni des sources et cite-les dans une section "Sources".
"""

    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    for idx, src in enumerate(sources, start=1):
        contents.append({
            "role": "user",
            "parts": [{"text": f"--- Contenu Source {idx} ({src}) ---\n{fetch_text(src)[:4000]}"}]
        })
    
    # MODIFICATION 2 : On utilise "generation_config" et "GenerationConfig"
    generation_config = GenerationConfig(
        temperature=0.3,
        max_output_tokens=1200
    )

    resp = client.models.generate_content(
        # MODIFICATION 3 : J'utilise un nom de modèle plus standard au cas où
        model="gemini-1.5-pro-latest",
        contents=contents,
        generation_config=generation_config
    )

    text = resp.text or ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {
            "title": topic[:120],
            "dek": "",
            "body": "<p>" + text.replace("\n", "<br/>") + "</p>",
            "bullets": [],
            "meta": {"keywords": [], "description": topic[:150]}
        }
    return data
