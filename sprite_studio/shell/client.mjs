const base = '/sprite-studio/v1/';
export async function request(action, body, query = {}) {
  const response = await fetch(base + action + '?' + new URLSearchParams(query), body === undefined ? {} : {
    method:'POST', headers:body instanceof FormData ? {} : {'Content-Type':'application/json'},
    body:body instanceof FormData ? body : JSON.stringify(body)
  });
  const result = await response.json();
  if (!response.ok) throw Error(result.error || 'Studio could not complete the request.');
  return result;
}
