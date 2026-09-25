// Production frontend server.
//
// Serves the built React SPA and proxies /api/* to the private backend
// Container App, forwarding only the Azure Easy Auth identity headers that
// Azure injects at the frontend boundary. The browser never talks to the
// backend directly — the backend is not publicly reachable.
import http from 'node:http';
import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST_DIR = path.join(__dirname, 'dist');
const PORT = process.env.PORT ? Number(process.env.PORT) : 5173;
const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || '';

const BACKEND_URL = BACKEND_BASE_URL
  ? new URL(BACKEND_BASE_URL)
  : null;

if (BACKEND_URL) {
  if (BACKEND_URL.protocol !== 'https:') {
    throw new Error('BACKEND_BASE_URL must use HTTPS');
  }
}

// The only identity headers trusted and forwarded to the backend.
const IDENTITY_HEADERS = [
  'x-ms-client-principal',
  'x-ms-client-principal-id',
  'x-ms-client-principal-name',
  'x-ms-client-principal-idp',
];

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
};

function proxyToBackend(req, res) {
  if (!BACKEND_BASE_URL) {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end('BACKEND_BASE_URL is not configured');
    return;
  }

  if (
    !req.url.startsWith('/api/') ||
    req.url.includes('..')
  ) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    res.end('Invalid API path');
    return;
  }

  const backendUrl = BACKEND_URL;
  const client = https;

  const forwardedHeaders = {};
  for (const [key, value] of Object.entries(req.headers)) {
    const lowerKey = key.toLowerCase();
    if (lowerKey === 'host') continue;
    // Strip any client-supplied principal headers that aren't the exact
    // identity headers Azure Easy Auth injects — never trust the browser.
    if (lowerKey.startsWith('x-ms-client-principal') && !IDENTITY_HEADERS.includes(lowerKey)) continue;
    forwardedHeaders[key] = value;
  }

  const proxyReq = client.request(
    {
      protocol: backendUrl.protocol,
      hostname: backendUrl.hostname,
      port: backendUrl.port || undefined,
      path: req.url,
      method: req.method,
      headers: forwardedHeaders,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on('error', (err) => {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end(`Backend proxy error: ${err.message}`);
  });

  req.pipe(proxyReq);
}

function serveStatic(req, res) {
  const urlPath = req.url.split('?')[0];
  let filePath = path.join(DIST_DIR, decodeURIComponent(urlPath));

  // Prevent path traversal outside dist/.
  if (!filePath.startsWith(DIST_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || stats.isDirectory()) {
      filePath = path.join(DIST_DIR, 'index.html');
    }
    fs.readFile(filePath, (readErr, data) => {
      if (readErr) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      const ext = path.extname(filePath);
      res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
      res.end(data);
    });
  });
}

const server = http.createServer((req, res) => {
  // Note: Azure Easy Auth's /.auth/* routes are intercepted by the platform
  // edge before reaching this container, so no special-casing is needed here.
  if (req.url.startsWith('/api/')) {
    proxyToBackend(req, res);
    return;
  }
  serveStatic(req, res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Frontend server listening on port ${PORT}`);
  console.log(`Proxying /api/* to ${BACKEND_BASE_URL || '(BACKEND_BASE_URL not configured)'}`);
});
