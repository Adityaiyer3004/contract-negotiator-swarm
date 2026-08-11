FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests and install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy application source code and build Next.js production bundle
COPY frontend/ ./
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3001

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3001

CMD ["npm", "run", "start", "--", "-p", "3001"]
