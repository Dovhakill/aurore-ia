// netlify/functions/gnews-proxy.js
// Cette fonction sert de relais sécurisé vers l'API GNews.
// On utilise 'require' pour la compatibilité avec les fonctions standards Netlify
const fetch = require('node-fetch');

exports.handler = async (event) => {
  // Récupère nos secrets depuis les variables d'environnement de Netlify
  const GNEWS_KEY = process.env.GNEWS_API_KEY;
  const INTERNAL_TOKEN = process.env.AURORE_BLOBS_TOKEN;

  // Étape de sécurité : on vérifie que l'appel vient bien de notre script Python
  if (event.headers["x-aurore-token"] !== INTERNAL_TOKEN) {
    return { statusCode: 401, body: "Unauthorized" };
  }

  // Construit l'URL pour appeler GNews
  const apiUrl = `https://gnews.io/api/v4/top-headlines?lang=fr&max=40&apikey=${GNEWS_KEY}`;

  try {
    const response = await fetch(apiUrl);
    if (!response.ok) {
      // Si GNews renvoie une erreur, on la transmet à notre script
      return { statusCode: response.status, body: await response.text() };
    }
    const data = await response.json();
    
    // Si tout va bien, on renvoie la réponse de GNews (les articles) à notre script Python
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    };

  } catch (error) {
    return { statusCode: 500, body: JSON.stringify({ message: "Erreur interne du proxy", details: error.message }) };
  }
};
