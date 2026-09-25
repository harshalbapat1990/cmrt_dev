import axios from 'axios';

// Deployed builds leave VITE_API_URL unset, so BASE_URL is '' and requests go
// to same-origin /api — server.js proxies those to the private backend and
// forwards Azure Easy Auth identity headers. VITE_API_URL is only meant for
// local dev, where it points directly at a locally running backend.
const buildTimeUrl =
  typeof import.meta.env !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL
    : '';

const runtimeWindowUrl =
  typeof window !== 'undefined' && (window as any).__API_URL
    ? (window as any).__API_URL
    : '';

const BASE_URL = buildTimeUrl || runtimeWindowUrl || '';

const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
  timeout: 60000,
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error);
  }
);

export default http;
