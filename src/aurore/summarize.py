import os
import google.generativeai as genai

def summarize_article(article_content, config):
    """Génère un résumé de l'article en utilisant le prompt configuré."""
    if not article_content:
        print("Le contenu de l'article est vide, impossible de résumer.")
        return None, None
        
    print("Génération du résumé avec Gemini...")
    try:
        gemini_api_key = os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-pro')

        prompt = config['gemini_prompt'] + f"\n\nContenu à analyser:\n{article_content}"
        
        response = model.generate_content(prompt)
        
        parts = response.text.split('\n', 1)
        if len(parts) < 2:
            print("Réponse de l'IA mal formatée (pas de saut de ligne).")
            return None, None
            
        title = parts[0].replace("#", "").strip()
        summary_markdown = parts[1].strip()
        
        print(f"Résumé généré avec succès. Titre : {title}")
        return title, summary_markdown
    except Exception as e:
        print(f"Erreur critique lors de la génération du résumé : {e}")
        return None, None
