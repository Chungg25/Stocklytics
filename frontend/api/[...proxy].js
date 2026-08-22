export const config = {
  runtime: 'edge',
};

export default async function handler(request) {
  try {
    const url = new URL(request.url);
    const hfUrl = process.env.HUGGINGFACE_URL;
    const hfToken = process.env.HUGGINGFACE_TOKEN;

    if (!hfUrl) {
      return new Response(JSON.stringify({ error: "Missing HUGGINGFACE_URL environment variable in Vercel" }), { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Forward the path and query string to Hugging Face
    // Example: request to /api/chat -> forwards to https://<your-space>.hf.space/api/chat
    const targetUrl = `${hfUrl.replace(/\/$/, '')}${url.pathname}${url.search}`;

    const headers = new Headers(request.headers);
    // Add Hugging Face Authorization token for Private Spaces
    if (hfToken) {
      headers.set('Authorization', `Bearer ${hfToken}`);
    }
    
    // Remove host header so fetch automatically sets the correct one for HF
    headers.delete('host');
    headers.delete('referer');

    const fetchOptions = {
      method: request.method,
      headers: headers,
      redirect: 'manual'
    };

    // Forward body if it's not a GET/HEAD request
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      fetchOptions.body = request.body;
      // Duplex is required for streaming request bodies in Edge functions
      fetchOptions.duplex = 'half';
    }

    const response = await fetch(targetUrl, fetchOptions);

    // Return the response directly to the client (supports streaming out of the box)
    return new Response(response.body, {
      status: response.status,
      headers: response.headers
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { 
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
