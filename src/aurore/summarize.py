# src/aurore/summarize.py

from typing import Sequence
import requests
from bs4 import BeautifulSoup
import json
# MODIFICATION 1: On importe la bibliothèque entière et on lui donne un alias "genai"
import google.generativeai as genai
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
    except Exception as e:
        print(f"Erreur de scraping sur {url}: {e}")
        return ""

def synthesize_neutral(topic: str, sources: Sequence[str]) -> dict:
    genai.configure(api_key=Settings.GEMINI_API_KEY)

    # MODIFICATION : On construit le prompt dynamiquement
    
    # Partie 1 : Les instructions générales
    prompt_instructions = f"""
Tu es un journaliste factuel qui écrit en français.
Fusionne les informations des {len(sources)} source(s) suivante(s) en un article neutre et clair.
Répond EXCLUSIVEMENT en JSON valide.

Le format doit être :
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
"""
    # Partie 2 : La liste des URLs
    source_list = "\n".join([f"{i}. {url}" for i, url in enumerate(sources, 1)])
    
    final_prompt = prompt_instructions + source_list

    # On envoie d'abord les instructions et la liste des sources
    contents = [{"role": "user", "parts": [{"text": final_prompt}]}]
    
    # Ensuite, on envoie le contenu de chaque source
    for idx, src in enumerate(sources, start=1):
        contents.append({
            "role": "user",
            "parts": [{"text": f"--- Contenu Source {idx} ({src}) ---\n{fetch_text(src)[:8000]}"}]
        })
    
    # ... (le reste de la fonction pour appeler Gemini ne change pas)
    generation_config = GenerationConfig(
        temperature=0.3,
        max_output_tokens=2048,
        response_mime_type="application/json",
    )
    model = genai.GenerativeModel("gemini-pro")
    resp = model.generate_content(
        contents=contents,
        generation_config=generation_config
    )
    
    text = resp.text or "{}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Erreur de décodage JSON. Réponse de l'IA:\n%s", text)
        return {
            "title": topic[:120], "dek": "", "body": "<p>Erreur de génération de contenu.</p>",
            "bullets": [], "meta": {"keywords": [], "description": topic[:150]}
        }
    return data
