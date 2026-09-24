# Frontend Dockerfile - Development with HMR
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy frontend code (will be overridden by mount in dev)
COPY . .

# Expose port for Vite dev server
EXPOSE 5173

# Run Vite dev server with HMR support
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
