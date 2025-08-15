const { getStore } = require("@netlify/blobs");

exports.handler = async (event) => {
  console.log("--- FONCTION BLOBS-PROXY INVOQUÉE ---");
  
  try {
    const secret = process.env.AURORE_BLOBS_TOKEN;
    const got = event.headers["x-aurore-token"];

    console.log(`Méthode reçue: ${event.httpMethod}`);

    if (!secret || got !== secret) {
      console.error("ERREUR: Token invalide ou manquant.");
      return { statusCode: 401, body: "Unauthorized" };
    }
    console.log("Token validé avec succès.");

    const store = getStore("aurore-memory");
    console.log("Magasin 'aurore-memory' récupéré.");

    if (event.httpMethod === "GET") {
      const key = event.queryStringParameters.key;
      console.log(`Mode GET - Clé à vérifier : ${key}`);
      if (!key) {
        console.error("ERREUR: Clé manquante dans la requête GET.");
        return { statusCode: 400, body: "Missing key" };
      }

      const val = await store.get(key);
      if (!val) {
        console.log(`Résultat GET: Clé '${key}' non trouvée.`);
        return { statusCode: 404, body: "Not found" };
      }
      
      console.log(`Résultat GET: Clé '${key}' trouvée.`);
      return { statusCode: 200, body: val };
    }

    if (event.httpMethod === "POST") {
      console.log("Mode POST - Corps de la requête :", event.body);
      const body = JSON.parse(event.body);
      const { key, meta } = body || {};
      
      if (!key) {
        console.error("ERREUR: Clé manquante dans la requête POST.");
        return { statusCode: 400, body: "Missing key" };
      }
      
      console.log(`Action POST: Sauvegarde de la clé '${key}'`);
      await store.setJSON(key, meta || {});
      console.log("Action POST: Sauvegarde réussie.");
      
      return { statusCode: 201, body: "OK" };
    }

    return { statusCode: 405, body: "Method Not Allowed" };

  } catch (err) {
    console.error("--- ERREUR FATALE DANS LA FONCTION ---", err);
    return { statusCode: 500, body: `Internal Server Error: ${err.message}` };
  }
};
