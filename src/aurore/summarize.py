from typing import Sequence
import requests
from bs4 import BeautifulSoup
import json
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from .config import Settings
import logging

logger = logging.getLogger("aurore")

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
        logger.warning("Erreur de scraping sur %s: %s", url, e)
        return ""

def synthesize_neutral(topic: str, sources: Sequence[str]) -> dict:
    genai.configure(api_key=Settings.GEMINI_API_KEY)

    prompt_instructions = f"""
Tu es un journaliste d'investigation pour le média "L'Horizon Libre". Ton style est neutre, factuel et approfondi.
Fusionne les informations des {len(sources)} source(s) suivante(s) en un article de presse complet (environ 400 mots).
Structure l'article avec une introduction claire qui présente le sujet, plusieurs paragraphes de développement qui explorent les différents angles et contextes, et une brève conclusion.
Utilise des balises `<strong>` pour mettre en évidence les noms, les lieux ou les chiffres importants.
Répond EXCLUSCLUSIVEMENT en JSON valide.

Le format doit être :
{{ 
  "title": "Titre journalistique, percutant et informatif (10-15 mots)",
  "dek": "Chapeau introductif de 2-3 phrases qui résume l'essentiel (Qui, Quoi, Où, Quand, Pourquoi).",
  "body": "<p>Introduction...</p><p>Développement...</p><p>Développement supplémentaire...</p><p>Conclusion...</p>",
  "bullets": ["Point clé factuel 1", "Point clé factuel 2", "Point clé factuel 3"],
  "meta": {{
    "keywords": ["journalisme", "analyse", "enquête"],
    "description": "Phrase unique de 150-160 caractères pour le SEO, résumant l'article."
  }}
}}

Sujet : {topic}
Sources :
"""

    source_list = "\n".join([f"{i}. {url}" for i, url in enumerate(sources, 1)])
    final_prompt = prompt_instructions + source_list

    contents = [{"role": "user", "parts": [{"text": final_prompt}]}]
    
    for idx, src in enumerate(sources, start=1):
        contents.append({
            "role": "user",
            "parts": [{"text": f"--- Contenu Source {idx} ({src}) ---\n{fetch_text(src)[:8000]}"}]
        })

    generation_config = GenerationConfig(
        temperature=0.3,
        max_output_tokens=2048,
        response_mime_type="application/json",
    )
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    
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
