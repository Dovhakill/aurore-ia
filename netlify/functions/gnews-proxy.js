// netlify/functions/gnews-proxy.js
const fetch = require('node-fetch');

exports.handler = async (event) => {
  const GNEWS_KEY = process.env.GNEWS_API_KEY;
  const INTERNAL_TOKEN = process.env.AURORE_BLOBS_TOKEN;

  if (event.headers["x-aurore-token"] !== INTERNAL_TOKEN) {
    return { statusCode: 401, body: "Unauthorized" };
  }

  const apiUrl = `https://gnews.io/api/v4/top-headlines?lang=fr&max=40&apikey=${GNEWS_KEY}`;

  try {
    // MODIFICATION : On ajoute le header User-Agent à l'appel fetch
    const response = await fetch(apiUrl, {
      headers: {
        'User-Agent': 'Aurore/1.0 (Netlify Proxy for L\'Horizon Libre)'
      }
    });
    
    if (!response.ok) {
      return { statusCode: response.status, body: await response.text() };
    }
    const data = await response.json();
    
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    };

  } catch (error) {
    return { statusCode: 500, body: JSON.stringify({ message: "Erreur du proxy", details: error.message }) };
  }
};
