const { getStore } = require("@netlify/blobs");
exports.handler = async function (event) {
  const secret = process.env.AURORE_BLOBS_TOKEN;
  const got = event.headers["x-aurore-token"] || event.headers["X-AURORE-TOKEN"];
  if (!secret || got !== secret) return { statusCode: 401, body: "Unauthorized" };
  const store = getStore("aurore-memory");
  if (event.httpMethod === "GET") {
    const key = (event.queryStringParameters || {}).key;
    if (!key) return { statusCode: 400, body: "Missing key" };
    const val = await store.get(key);
    if (!val) return { statusCode: 404, body: "Not found" };
    return { statusCode: 200, body: val };
  }
  if (event.httpMethod === "POST") {
    try {
      const { key, meta } = JSON.parse(event.body || "{}");
      if (!key) return { statusCode: 400, body: "Missing key" };
      await store.setJSON(key, meta || {});
      return { statusCode: 201, body: "OK" };
    } catch {
      return { statusCode: 400, body: "Bad Request" };
    }
  }
  return { statusCode: 405, body: "Method Not Allowed" };
};