# -*- coding: utf-8 -*-
import os, re
import google.generativeai as genai

def _parse_tags(text: str):
    t = re.search(r'<TITRE>(.*?)</TITRE>', text, re.DOTALL | re.IGNORECASE)
    s = re.search(r'<RESUME>(.*?)</RESUME>', text, re.DOTALL | re.IGNORECASE)
    if t and s:
        return t.group(1).strip(), s.group(1).strip()
    return None, None

def summarize_article(article_content: str, gemini_prompt: str):
    """
    Utilise TON prompt (balises) et renvoie (title, summary).
    - Aucune réinvention: on envoie tel quel le prompt + le contenu.
    """
    if not article_content:
        return None, None

    try:
        api_key = os.environ["GEMINI_API_KEY"]
    except KeyError:
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
                "response_mime_type": "text/plain",
            },
        )
        # On construit un simple prompt utilisateur basé sur ton gemini_prompt
        prompt = f"{gemini_prompt.strip()}\n\nArticle :\n\"\"\"\n{article_content}\n\"\"\""
        resp = model.generate_content(prompt)

        text = getattr(resp, "text", "") or ""
        title, summary = _parse_tags(text)
        if not (title and summary):
            print(f"Réponse IA non exploitable: {text[:400]}")
            return None, None
        return title, summary

    except Exception as e:
        print(f"Erreur Gemini: {e}")
        return None, None
