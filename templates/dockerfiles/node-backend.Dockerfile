# Node.js backend Dockerfile
# Агент: подставь значения переменных перед использованием.
# ${NODE_VERSION} — версия Node.js (по умолчанию 20)
# ${INSTALL_CMD} — команда установки зависимостей (npm ci / yarn install --frozen-lockfile / pnpm install --frozen-lockfile)
# ${BUILD_CMD} — команда сборки (npm run build). Если проект на чистом JS без билда — удали builder-стадию и BUILD_CMD.
# ${START_CMD} — команда запуска (node dist/index.js / npm start / node src/index.js)
# ${PORT} — порт приложения

# === Вариант A: TypeScript / проект с билд-шагом ===
FROM node:${NODE_VERSION}-alpine AS builder
WORKDIR /app
COPY package*.json yarn.lock* pnpm-lock.yaml* bun.lockb* ./
RUN ${INSTALL_CMD}
COPY . .
RUN ${BUILD_CMD}

FROM node:${NODE_VERSION}-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:${PORT}/health || exit 1
CMD [${START_CMD}]

# === Вариант B: JavaScript без билд-шага (раскомментируй и удали всё выше) ===
# FROM node:${NODE_VERSION}-alpine
# WORKDIR /app
# COPY package*.json yarn.lock* pnpm-lock.yaml* bun.lockb* ./
# RUN ${INSTALL_CMD} --production
# COPY . .
# EXPOSE ${PORT}
# HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
#   CMD wget -qO- http://localhost:${PORT}/health || exit 1
# CMD [${START_CMD}]
