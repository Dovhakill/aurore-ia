import os, re, sys, json
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

def summarize_article(article_content: str, config: dict):
    if not article_content:
        print("Le contenu de l'article est vide, impossible de résumer.")
        return None, None
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config={
                "temperature": 0.4,
                "top_p": 0.95,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json",
            },
            system_instruction=(
                "Tu es Aurore, une IA de synthèse d'information pour Horizon Network. "
                "Neutralité stricte. Pas d'opinion. Sortie: JSON valide uniquement."
            ),
        )
        user_prompt = (
            "Voici le texte brut d'un article. Analyse-le et retourne un objet JSON "
            'avec la structure exacte: {"title":"...","summary":"...","source_name":"..."}.\n\n'
            "Rappels: titre 4-10 mots, résumé 3-5 phrases neutres (100-150 mots), source_name = média d'origine.\n\n"
            "Article source:\n\"\"\"\n" + article_content + "\n\"\"\"\n"
        )
        resp = model.generate_content(user_prompt)
        text = getattr(resp, "text", None)
        if text is None:
            # SDK fallback
            try:
                text = resp.candidates[0].content.parts[0].text
            except Exception:
                text = ""
        title, summary, _ = _parse_as_json(text)
        if not (title and summary):
            title, summary, _ = _parse_as_tags(text)
        if not (title and summary):
            print(f"Réponse IA non exploitable: {text}")
            return None, None
        return title.strip(), summary.strip()
    except KeyError:
        print("Erreur critique : Le secret GEMINI_API_KEY est manquant.")
        return None, None
    except Exception as e:
        print(f"Erreur inattendue lors de la génération du résumé avec Gemini : {e}")
        return None, None
