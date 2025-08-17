def run_once():
    Settings.validate()
    candidates = fetch_top_fr(page_size=20)
    
    if not candidates:
        logger.info("Aucun article trouvé.")
        return

    first_article = candidates[0]
    title = first_article.get("title") or ""
    if not title:
        logger.info("Le premier article n'a pas de titre. On s'arrête.")
        return

    logger.info("Tentative de traitement pour l'article : %s", title)
    
    sources = find_additional_sources(title, first_article.get("url"), max_sources=3)
    if not sources:
        return

    key = topic_key(title, sources)
    if seen(key):
        logger.info("Déjà vu (skipping): %s", title)
        return

    try:
        data = synthesize_neutral(title, sources)
        art_title = data.get("title", title)
        category = data.get("category", "International")
        image_details = find_unsplash_image(art_title)
        body = data.get("body", "")
        bullets = data.get("bullets", [])
        meta = data.get("meta", {})
        dek = data.get("dek", "")
        
        # On ajoute la variable 'category' dans l'appel
        path, html, slug = render_article("templates", art_title, body, sources, category, bullets=bullets, meta=meta, dek=dek, image=image_details)
        
        pr_url = open_pr(
            repo_fullname=Settings.GH_SITE_REPO, token=Settings.GH_TOKEN,
            path=path, html=html, author_name=Settings.GH_AUTHOR_NAME,
            author_email=Settings.GH_AUTHOR_EMAIL, title=art_title
        )
        
        mark(key, {"title": art_title, "pr": pr_url, "sources": sources})
        logger.info("SUCCÈS ! PR créée : %s", pr_url)
        
    except Exception as e:
        logger.exception("Échec du traitement de l'article %s: %s", title, e)

    logger.info("Traitement du premier article terminé. Arrêt du script.")
