const { getStore } = require("@netlify/blobs");

exports.handler = async (event) => {
  try {
    const secret = process.env.AURORE_BLOBS_TOKEN;
    const got = event.headers["x-aurore-token"];

    if (!secret || got !== secret) {
      return { statusCode: 401, body: "Unauthorized" };
    }

    const store = getStore({
      name: "aurore-memory",
      siteID: process.env.NETLIFY_SITE_ID,
      token: process.env.NETLIFY_API_TOKEN,
    });

    if (event.httpMethod === "GET") {
      const key = event.queryStringParameters.key;
      if (!key) return { statusCode: 400, body: "Missing key" };
      const val = await store.get(key);
      if (!val) return { statusCode: 404, body: "Not found" };
      return { statusCode: 200, body: val };
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
    console.error("[ERREUR BLOBS-PROXY]", err);
    return { statusCode: 500, body: `Internal Server Error: ${err.message}` };
  }
};
