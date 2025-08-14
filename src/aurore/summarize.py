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
    # MODIFICATION 2: On configure la clé API une seule fois
    genai.configure(api_key=Settings.GEMINI_API_KEY)

    prompt = f"""
Tu es un journaliste factuel expert en SEO qui écrit en français.
Fusionne les informations des sources en un article neutre et clair.
Répond EXCLUSIVEMENT en JSON valide.

Le champ "body" doit contenir du HTML sémantique : utilise des paragraphes `<p>`, des listes `<ul><li>`, et des `<strong>` pour les termes importants. Ne jamais utiliser de balise `<h1>` ou `<h2>`.
Le champ "dek" (chapeau) est obligatoire et doit faire entre 20 et 40 mots.
Le champ "meta.description" doit être une phrase unique de 150-160 caractères maximum.
Le champ "meta.keywords" doit contenir entre 3 et 5 mots-clés pertinents.

Le format doit être :
{{
  "title": "Titre court et précis (50-70 caractères)",
  "dek": "Chapeau introductif de 1-2 phrases, engageant et informatif.",
  "body": "<p>HTML structuré de l'article...</p>",
  "bullets": ["Point clé 1", "Point clé 2", "Point clé 3"],
  "meta": {{
    "keywords": ["mot", "clé", "pertinent"],
    "description": "Phrase unique et descriptive optimisée pour le SEO (150-160 caractères)."
  }}
}}

Sujet : {topic}

Sources :
1. {sources[0]}
2. {sources[1]}
3. {sources[2]}
"""

    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    for idx, src in enumerate(sources, start=1):
        contents.append({
            "role": "user",
            "parts": [{"text": f"--- Contenu Source {idx} ({src}) ---\n{fetch_text(src)[:8000]}"}]
        })

    generation_config = GenerationConfig(
        temperature=0.3,
        max_output_tokens=2048,
        # On spécifie le type de réponse attendu comme JSON
        response_mime_type="application/json",
    )
    
    # MODIFICATION 3: On crée une instance du modèle et on génère le contenu
    model = genai.GenerativeModel("gemini-1.0-pro")
    
    resp = model.generate_content(
        contents=contents,
        generation_config=generation_config
    )

    text = resp.text or "{}"
    try:
        # La réponse de l'IA est déjà en JSON, plus besoin de json.loads sur le texte brut
        data = json.loads(text)
    except json.JSONDecodeError:
        print(f"Erreur de décodage JSON. Réponse de l'IA:\n{text}")
        return {
            "title": topic[:120], "dek": "", "body": "<p>Erreur de génération de contenu.</p>",
            "bullets": [], "meta": {"keywords": [], "description": topic[:150]}
        }
    return data
