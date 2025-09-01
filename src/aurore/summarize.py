import os
import re
import sys  # <--- IMPORT AJOUTÉ
import google.generativeai as genai

def parse_gemini_response(response_text):
    try:
        title_match = re.search(r'<TITRE>(.*?)</TITRE>', response_text, re.DOTALL)
        summary_match = re.search(r'<RESUME>(.*?)</RESUME>', response_text, re.DOTALL)

        if title_match and summary_match:
            title = title_match.group(1).strip()
            summary = summary_match.group(1).strip()
            return title, summary
        else:
            print(f"Réponse de l'IA mal formatée (balises manquantes) : {response_text}")
            return None, None
    except Exception as e:
        print(f"Erreur lors du parsing de la réponse de l'IA : {e}")
        return None, None

def summarize_article(article_content, config):
    if not article_content:
        print("Le contenu de l'article est vide, impossible de résumer.")
        return None, None
        
    print("Génération du résumé avec Gemini...")
    try:
        gemini_api_key = os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = config['gemini_prompt'] + f"\n\nARTICLE À ANALYSER:\n{article_content}"
        
        response = model.generate_content(prompt)
        
        title, summary_markdown = parse_gemini_response(response.text)
        
        if title and summary_markdown:
            print(f"Résumé généré avec succès. Titre : {title}")
            return title, summary_markdown
        else:
            return None, None

    except KeyError:
        print("Erreur critique : Le secret GEMINI_API_KEY est manquant.")
        sys.exit(1) # <--- ON FORCE L'ÉCHEC DU WORKFLOW ICI
    except Exception as e:
        print(f"Erreur critique lors de la génération du résumé : {e}")
        sys.exit(1) # <--- ON FORCE L'ÉCHEC DU WORKFLOW ICI
