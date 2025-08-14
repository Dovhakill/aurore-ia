// On utilise 'require' au lieu de 'import' pour la compatibilité
const { getStore } = require("@netlify/blobs");

// C'est la syntaxe pour une fonction Netlify "Standard"
exports.handler = async (event) => {
  const secret = process.env.AURORE_BLOBS_TOKEN;
  // Les en-têtes sont dans event.headers
  const got = event.headers["x-aurore-token"];

  if (!secret || got !== secret) {
    return { statusCode: 401, body: "Unauthorized" };
  }

  const store = getStore("aurore-memory");

  // La méthode de la requête est dans event.httpMethod
  if (event.httpMethod === "GET") {
    // Les paramètres d'URL sont dans event.queryStringParameters
    const key = event.queryStringParameters.key;
    if (!key) {
      return { statusCode: 400, body: "Missing key" };
    }

    const val = await store.get(key);
    if (!val) {
      return { statusCode: 404, body: "Not found" };
    }
    
    return { statusCode: 200, body: val };
  }

  if (event.httpMethod === "POST") {
    try {
      // Le corps de la requête est une chaîne de caractères qu'il faut parser
      const body = JSON.parse(event.body);
      const { key, meta } = body || {};
      if (!key) {
        return { statusCode: 400, body: "Missing key" };
      }

      await store.setJSON(key, meta || {});
      return { statusCode: 201, body: "OK" };
    } catch (err) {
      return { statusCode: 400, body: "Bad Request: Invalid JSON" };
    }
  }

  return { statusCode: 405, body: "Method Not Allowed" };
};
