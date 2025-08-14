from typing import Sequence
import requests
from bs4 import BeautifulSoup
import json
from google.genai import Client
from google.genai.types import ResponseParams
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
Tu es un journaliste factuel expert en SEO qui écrit en français.
Fusionne les informations des sources en un article neutre et clair.
Répond EXCLUSIVEMENT en JSON valide.

Contraintes :
- "body": HTML sémantique uniquement (balises <p>, <ul><li>, <strong>), pas de <h1>/<h2>.
- "dek": obligatoire, 20–40 mots.
- "meta.description": 150–160 caractères max, une seule phrase.
- "meta.keywords": 3 à 5 mots-clés pertinents.

Format attendu :
{{ 
  "title": "Titre court et précis (50–70 caractères)",
  "dek": "Chapeau introductif de 1–2 phrases, engageant et informatif.",
  "body": "<p>HTML structuré de l'article…</p>",
  "bullets": ["Point clé 1", "Point clé 2", "Point clé 3"],
  "meta": {{
    "keywords": ["mot", "clé", "pertinent"],
    "description": "Phrase unique optimisée SEO (150–160 caractères)."
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
            "parts": [{"text": f"--- Contenu Source {idx} ({src}) ---\n{fetch_text(src)[:4000]}"}]
        })

    resp = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=contents,
        config=ResponseParams(temperature=0.3, max_output_tokens=1200)
    )

    text = resp.text or ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {
            "title": topic[:120],
            "dek": "",
            "body": "<p>" + text.replace("\\n", "<br/>") + "</p>",
            "bullets": [],
            "meta": {"keywords": [], "description": topic[:150]}
        }
    return data