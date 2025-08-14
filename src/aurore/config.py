# src/aurore/config.py
import os

class Settings:
    # On change la clé API
    GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY")
    
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GH_TOKEN = os.environ.get("GH_TOKEN")
    GH_SITE_REPO = os.environ.get("GH_SITE_REPO")
    GH_AUTHOR_NAME = os.environ.get("GH_AUTHOR_NAME", "Aurore Bot")
    GH_AUTHOR_EMAIL = os.environ.get("GH_AUTHOR_EMAIL", "bot@horizon-libre.example")
    BLOBS_PROXY_URL = os.environ.get("BLOBS_PROXY_URL")
    AURORE_BLOBS_TOKEN = os.environ.get("AURORE_BLOBS_TOKEN")
    USER_AGENT = "Aurore/1.0 (+https://l-horizon-libre.fr)"
    MAX_ARTICLES_PER_RUN = int(os.environ.get("MAX_ARTICLES_PER_RUN", "1"))

    @classmethod
    def validate(cls):
        missing = []
        # On vérifie la nouvelle clé
        for attr in ["GNEWS_API_KEY", "GEMINI_API_KEY", "GH_TOKEN", "GH_SITE_REPO", "BLOBS_PROXY_URL", "AURORE_BLOBS_TOKEN"]:
            if not getattr(cls, attr):
                missing.append(attr)
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
