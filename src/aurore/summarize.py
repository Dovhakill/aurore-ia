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

   prompt_instructions = f"""
Tu es un journaliste d'investigation pour le média "L'Horizon Libre". Ton style est neutre, factuel et approfondi.
Fusionne les informations des {len(sources)} source(s) suivante(s) en un article de presse complet (environ 400 mots).
Structure l'article avec une introduction claire qui présente le sujet, plusieurs paragraphes de développement qui explorent les différents angles et contextes, et une brève conclusion.
Utilise des balises `<strong>` pour mettre en évidence les noms, les lieux ou les chiffres importants.
Répond EXCLUSIVEMENT en JSON valide.

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
