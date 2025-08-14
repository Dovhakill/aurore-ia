const { getStore } = require("@netlify/blobs");
// On importe le module de cryptographie de Node.js
const crypto = require("crypto");

exports.handler = async (event) => {
  const secret = process.env.AURORE_BLOBS_TOKEN;
  
  // --- LIGNES DE DÉBOGAGE ---
  if (secret) {
    const hash = crypto.createHash('sha256').update(secret).digest('hex');
    console.log(`[DEBUG NETLIFY] Empreinte du token attendu : ${hash.substring(0, 10)}...`);
  } else {
    console.log("[DEBUG NETLIFY] Le secret AURORE_BLOBS_TOKEN n'est PAS DÉFINI sur Netlify !");
  }
  // --- FIN DU DÉBOGAGE ---

  const got = event.headers["x-aurore-token"];
  if (!secret || got !== secret) {
    return { statusCode: 401, body: "Unauthorized" };
  }

  const store = getStore("aurore-memory");

  if (event.httpMethod === "GET") {
    const key = event.queryStringParameters.key;
    if (!key) return { statusCode: 400, body: "Missing key" };
    const val = await store.get(key);
    if (!val) return { statusCode: 404, body: "Not found" };
    return { statusCode: 200, body: val };
  }

  if (event.httpMethod === "POST") {
    try {
      const body = JSON.parse(event.body);
      const { key, meta } = body || {};
      if (!key) return { statusCode: 400, body: "Missing key" };
      await store.setJSON(key, meta || {});
      return { statusCode: 201, body: "OK" };
    } catch (err) {
      return { statusCode: 400, body: "Bad Request: Invalid JSON" };
    }
  }

  return { statusCode: 405, body: "Method Not Allowed" };
};
