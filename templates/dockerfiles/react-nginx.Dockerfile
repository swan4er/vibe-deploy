# Frontend SPA Dockerfile (React, Vue, Svelte, Angular, Astro)
# Агент: подставь значения переменных перед использованием.
# ${NODE_VERSION} — версия Node.js (по умолчанию 20)
# ${INSTALL_CMD} — команда установки (npm ci / yarn install --frozen-lockfile / pnpm install --frozen-lockfile)
# ${BUILD_OUTPUT_DIR} — директория результатов сборки:
#   Vite (React/Vue/Svelte) → dist
#   Create React App → build
#   Angular → dist
#   Gatsby → public
#   Astro → dist
#   Next.js (static export) → out

FROM node:${NODE_VERSION}-alpine AS builder
WORKDIR /app
COPY package*.json yarn.lock* pnpm-lock.yaml* bun.lockb* ./
RUN ${INSTALL_CMD}
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/${BUILD_OUTPUT_DIR} /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
