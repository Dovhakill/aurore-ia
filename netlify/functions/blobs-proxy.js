// Fonction "blobs-proxy" finale et sécurisée

exports.handler = async (event) => {
  console.log(`[INFO] Fonction blobs-proxy invoquée avec la méthode : ${event.httpMethod}`);

  // On importe les dépendances à l'intérieur pour isoler les erreurs
  const { getStore } = require("@netlify/blobs");
  const crypto = require("crypto");

  try {
    const secret = process.env.AURORE_BLOBS_TOKEN;
    if (!secret) {
        console.error("[ERREUR] La variable d'environnement AURORE_BLOBS_TOKEN est manquante sur Netlify.");
        return { statusCode: 500, body: "Configuration error: Missing token" };
    }
    
    const hash = crypto.createHash('sha256').update(secret).digest('hex');
    console.log(`[DEBUG] Empreinte du token attendu sur Netlify : ${hash.substring(0, 10)}...`);

    const got = event.headers["x-aurore-token"];
    if (!got || got !== secret) {
      console.warn("[ALERTE] Token invalide ou manquant dans la requête.");
      return { statusCode: 401, body: "Unauthorized" };
    }

    const store = getStore("aurore-memory");

    if (event.httpMethod === "GET") {
      const key = event.queryStringParameters.key;
      if (!key) return { statusCode: 400, body: "Missing key" };
      
      const val = await store.get(key);
      return val
        ? { statusCode: 200, body: val }
        : { statusCode: 404, body: "Not found" };
    }

    if (event.httpMethod === "POST") {
      const body = JSON.parse(event.body);
      const { key, meta } = body || {};
      if (!key) return { statusCode: 400, body: "Missing key" };

      await store.setJSON(key, meta || {});
      return { statusCode: 201, body: "OK" };
    }

    return { statusCode: 405, body: "Method Not Allowed" };

  } catch (err) {
    console.error("[ERREUR FATALE]", err);
    return { statusCode: 500, body: `Internal Server Error: ${err.message}` };
  }
};
