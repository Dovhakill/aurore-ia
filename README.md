# Aurore - Assistant journaliste autonome

Pipeline Python planifié (GitHub Actions) qui :
- récupère des news (NewsAPI),
- enrichit les sources,
- synthétise via Gemini,
- génère un HTML (Jinja2),
- ouvre une PR sur le site `horizon-libre-site`.

Mémoire des sujets via Netlify Blobs, exposée par une Netlify Function `blobs-proxy` sécurisée (X-AURORE-TOKEN).

## Déploiement rapide

1) Netlify (site horizon-libre-site)
- Ajouter `netlify/functions/blobs-proxy.js` dans le repo du site (voir ce dépôt).
- Ajouter la variable `AURORE_BLOBS_TOKEN` (secret).
- Installer la dépendance dans le site: `npm i @netlify/blobs`.

2) GitHub (repo Aurore)
- Secrets: `NEWSAPI_KEY`, `GEMINI_API_KEY`, `GH_TOKEN`, `GH_SITE_REPO`, `GH_AUTHOR_NAME`, `GH_AUTHOR_EMAIL`, `AURORE_BLOBS_TOKEN`.
- Variables: `BLOBS_PROXY_URL = https://<site>.netlify.app/.netlify/functions/blobs-proxy`.
- Le workflow `.github/workflows/aurore-cron.yml` tourne toutes les 10 min (déclenchable à la main).

3) Test local
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:NEWSAPI_KEY="..."
$env:GEMINI_API_KEY="..."
$env:GH_TOKEN="..."
$env:GH_SITE_REPO="owner/horizon-libre-site"
$env:GH_AUTHOR_NAME="Aurore Bot"
$env:GH_AUTHOR_EMAIL="bot@horizon-libre.example"
$env:AURORE_BLOBS_TOKEN="..."
$env:BLOBS_PROXY_URL="https://<site>.netlify.app/.netlify/functions/blobs-proxy"
python -m src.aurore

Sécurité: ne commit jamais de clés. Utilise GitHub Secrets & variables Netlify.