import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

let csrfToken = '';

export function setCsrfToken(token: string) {
  csrfToken = token;
}

client.interceptors.request.use((config) => {
  if (csrfToken && config.method !== 'get') {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

// On 403 try to refresh CSRF once then retry
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    // ПРОБЛЕМА: запрет доступа 403 повторно отправлял запрос, хотя CSRF мог быть корректным.
    // РЕШЕНИЕ: повторяем только при явно распознанной CSRF-ошибке и не более одного раза.
    const detail = String(error.response?.data?.detail ?? '');
    if (original && error.response?.status === 403 && /csrf/i.test(detail) && !original._csrfRetried) {
      original._csrfRetried = true;
      try {
        const { data } = await axios.get('/api/auth/csrf/', { withCredentials: true });
        setCsrfToken(data.csrfToken);
        original.headers['X-CSRFToken'] = data.csrfToken;
        return client(original);
      } catch {
        // fall through to original error
      }
    }
    return Promise.reject(error);
  },
);

export default client;
