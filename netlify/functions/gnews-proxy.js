const fetch = require('node-fetch');
const crypto = require("crypto");

exports.handler = async (event) => {
  const GNEWS_KEY = process.env.GNEWS_API_KEY;
  const INTERNAL_TOKEN = process.env.AURORE_BLOBS_TOKEN;

  // --- LIGNE DE DÉBOGAGE ---
  if (INTERNAL_TOKEN) {
    const hash = crypto.createHash('sha256').update(INTERNAL_TOKEN).digest('hex');
    console.log(`[DEBUG NETLIFY GNEWS] Empreinte du token attendu : ${hash.substring(0, 10)}...`);
  }
  // --- FIN DU DÉBOGAGE ---

  if (event.headers["x-aurore-token"] !== INTERNAL_TOKEN) {
    return { statusCode: 401, body: "Unauthorized" };
  }
  
  const apiUrl = `https://gnews.io/api/v4/top-headlines?lang=fr&max=40&apikey=${GNEWS_KEY}`;
  try {
    const response = await fetch(apiUrl, { headers: { 'User-Agent': 'Aurore/1.0' } });
    if (!response.ok) {
      return { statusCode: response.status, body: await response.text() };
    }
    const data = await response.json();
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
  } catch (error) {
    return { statusCode: 500, body: JSON.stringify({ message: "Erreur du proxy", details: error.message }) };
  }
};
