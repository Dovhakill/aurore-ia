# -*- coding: utf-8 -*-
import os
import re
from typing import List, Union, Tuple
import google.generativeai as genai

def _as_prompt_text(gemini_prompt: Union[str, List[str]]) -> str:
    """Accepte string ou liste de lignes, renvoie un unique prompt texte."""
    if isinstance(gemini_prompt, list):
        # On join proprement, en enlevant les espaces superflus
        return "\n".join([str(x).strip() for x in gemini_prompt if str(x).strip()])
    if isinstance(gemini_prompt, str):
        return gemini_prompt.strip()
    return "Voici un article. Résume-le en <TITRE> / <RESUME> de manière neutre et factuelle."

_TAG_TITRE = re.compile(r'<TITRE>(.*?)</TITRE>', re.DOTALL | re.IGNORECASE)
_TAG_RESUME = re.compile(r'<RESUME>(.*?)</RESUME>', re.DOTALL | re.IGNORECASE)

def _parse_tags(text: str) -> Tuple[str, str]:
    """Extrait <TITRE> et <RESUME>. Renvoie (title, summary) ou (None, None)."""
    if not text:
        return None, None
    t = _TAG_TITRE.search(text)
    s = _TAG_RESUME.search(text)
    if not (t and s):
        return None, None
    title = t.group(1).strip()
    summary = s.group(1).strip()
    return (title or None), (summary or None)

def summarize_article(article_content: str, gemini_prompt: Union[str, List[str]]):
    """
    Utilise TON prompt (string ou liste) et renvoie (title, summary).
    Le modèle doit répondre UNIQUEMENT avec <TITRE>...</TITRE><RESUME>...</RESUME>.
    """
    if not article_content:
        print("Contenu vide — résumés interdits.")
        return None, None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY manquant.")
        return None, None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={
                "temperature": 0.4,
                "top_p": 0.95,
                "max_output_tokens": 1024,
                "response_mime_type": "text/plain",  # on attend des balises texte
            },
        )

        prompt_text = _as_prompt_text(gemini_prompt)
        user_prompt = (
            f"{prompt_text}\n\n"
            f"Article :\n\"\"\"\n{article_content}\n\"\"\""
        )

        resp = model.generate_content(user_prompt)
        text = getattr(resp, "text", None)
        if text is None:
            # fallback SDK
            try:
                text = resp.candidates[0].content.parts[0].text
            except Exception:
                text = ""

        title, summary = _parse_tags(text)
        if not (title and summary):
            print(f"Réponse IA non exploitable (pas de balises): {text[:400]}")
            return None, None

        # Petites sécurités de forme
        title = " ".join(title.split())
        summary = summary.strip()

        return title, summary

    except Exception as e:
        print(f"Erreur Gemini: {e}")
        return None, None
