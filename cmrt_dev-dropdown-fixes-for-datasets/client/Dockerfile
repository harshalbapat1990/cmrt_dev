# FrontEnd
# Simple single-stage Dockerfile for React + Vite frontend
FROM node:20-slim

WORKDIR /app

# Disable npm strict SSL for installation (development only)
RUN npm config set strict-ssl false

# Copy package files and install dependencies
COPY package.json ./
RUN npm install

# Copy application code
COPY . .

# Declare build-time args for Vite
# VITE_API_URL is intentionally left unset in deployed builds — the browser
# calls same-origin /api, and server.js proxies it to BACKEND_BASE_URL at runtime.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the frontend application
RUN npm run build

# Runtime config: PORT for this server, BACKEND_BASE_URL for the private backend.
ENV PORT=5173
EXPOSE 5173

# Serve the built SPA and proxy /api/* to the private backend, forwarding
# only Azure Easy Auth identity headers.
CMD ["node", "server.js"]