# -*- coding: utf-8 -*-
"""
summarize.py
- Résumé via Gemini si clé disponible
- Fallback simple sans IA si la clé n'est pas fournie
"""
from __future__ import annotations

import re
from typing import Tuple, Union, List, Any, Dict
import os


def _join_prompt(prompt_cfg: Union[str, List[str]]) -> str:
    if isinstance(prompt_cfg, list):
        return "\n".join(str(x) for x in prompt_cfg)
    return str(prompt_cfg)


TAG_RE = re.compile(r"<TITRE>(.*?)</TITRE>.*?<RESUME>(.*?)</RESUME>", re.S | re.I)


def _extract_tags(text: str) -> Tuple[str, str]:
    m = TAG_RE.search(text or "")
    if not m:
        return "", ""
    title = m.group(1).strip()
    summary = m.group(2).strip()
    return title, summary


def _first_lines_as_fallback(article_text: str) -> Tuple[str, str]:
    """
    Fallback sans IA : titre = 90 premiers caractères de la 1ère phrase ;
    résumé = 3-4 paragraphes (si dispo).
    """
    text = (article_text or "").strip()
    if not text:
        return "", ""

    # titre naïf
    first_sentence = re.split(r"(?<=[\.\!\?])\s+", text, maxsplit=1)[0]
    title = first_sentence[:80].rstrip(" .,;:-") or first_sentence

    # 3 petits paragraphes
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    summary = "\n".join(paras[:4])

    return title, summary


def summarize_article(article_text: str, prompt_cfg: Union[str, List[str]]) -> Tuple[str, str]:
    """
    Retourne (title, summary).
    - Essaye Gemini si GEMINI_API_KEY est présent
    - Sinon fallback local
    """
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return _first_lines_as_fallback(article_text)

    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={
                "temperature": 0.4,
                "top_p": 0.95,
                "max_output_tokens": 700,
                "response_mime_type": "text/plain",
            },
        )

        sys_prompt = _join_prompt(prompt_cfg)
        prompt = f"{sys_prompt}\n\n<TEXTE_SOURCE>\n{article_text}\n</TEXTE_SOURCE>"
        resp = model.generate_content(prompt)
        out = (getattr(resp, "text", None) or "").strip()
        title, summary = _extract_tags(out)
        if not (title and summary):
            # fallback si le modèle n'a pas respecté le format
            return _first_lines_as_fallback(article_text)
        return title, summary

    except Exception as e:
        print(f"WARN summarize (Gemini): {e}")
        return _first_lines_as_fallback(article_text)
