// Fichier de test "Hello World" pour débugger la fonction Netlify

exports.handler = async (event) => {
  console.log("--- La fonction blobs-proxy a été appelée ! ---");
  console.log("Méthode HTTP reçue :", event.httpMethod);

  const response = {
    statusCode: 200,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: "Proxy is alive and responding!" }),
  };

  console.log("Réponse envoyée au script Python :", JSON.stringify(response));
  
  return response;
};
