import os
import re
import sys
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
        # La ligne correcte, sans faute de frappe
        gemini_api_key = os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        
        # J'ai vu que 'gemini_prompt' n'était pas dans ton config.json, je le retire pour éviter une autre erreur
        # prompt = config['gemini_prompt'] + f"\n\nARTICLE À ANALYSER:\n{article_content}"
        prompt_template = "Voici un article de presse. Crée un titre percutant et un résumé neutre et factuel. Le format de ta réponse doit être exclusivement : <TITRE>Ton titre</TITRE><RESUME>Ton résumé.</RESUME>"
        prompt = prompt_template + f"\n\nARTICLE À ANALYSER:\n{article_content}"

        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        title, summary_markdown = parse_gemini_response(response.text)
        
        if title and summary_markdown:
            print(f"Résumé généré avec succès. Titre : {title}")
            return title, summary_markdown
        else:
            return None, None

    except KeyError:
        # On met le bon message d'erreur pour le futur
        print("Erreur critique : Le secret GEMINI_API_KEY est manquant dans l'environnement.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur critique lors de la génération du résumé : {e}")
        sys.exit(1)
