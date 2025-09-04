# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import google.generativeai as genai

def _parse_as_json(text: str):
    try:
        obj = json.loads(text)
        return obj.get("title"), obj.get("summary"), obj.get("source_name")
    except Exception:
        return None, None, None

def _parse_as_tags(text: str):
    t = re.search(r'<TITRE>(.*?)</TITRE>', text, re.DOTALL)
    s = re.search(r'<RESUME>(.*?)</RESUME>', text, re.DOTALL)
    if t and s:
        return t.group(1).strip(), s.group(1).strip(), None
    return None, None, None

def parse_gemini_response(response_text):
    """Parse la réponse de Gemini pour extraire titre et résumé"""
    title, summary, _ = _parse_as_tags(response_text)
    if not (title and summary):
        title, summary, _ = _parse_as_json(response_text)
    return title, summary

def summarize_article(article_content: str, config: dict):
    if not article_content:
        print("Le contenu de l'article est vide, impossible de résumer.")
        return None, None
    
    try:
        gemini_api_key = os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # On assemble le prompt multi-lignes depuis la config
        prompt_text = "".join(config['gemini_prompt'])
        prompt = prompt_text + f"\n\nArticle source à analyser :\n{article_content}"
        
        response = model.generate_content(prompt)
        
        title, summary_markdown = parse_gemini_response(response.text)
        
        if title and summary_markdown:
            print(f"Résumé généré avec succès. Titre : {title}")
            return title, summary_markdown
        else:
            print(f"Réponse IA non exploitable: {response.text}")
            return None, None
            
    except KeyError:
        print("Erreur critique : Le secret GEMINI_API_KEY est manquant.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue lors de la génération du résumé avec Gemini : {e}")
        return None, None
