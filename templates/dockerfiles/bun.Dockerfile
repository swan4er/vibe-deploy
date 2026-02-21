# Bun Dockerfile
# Агент: подставь значения переменных перед использованием.
# ${BUN_VERSION} — версия Bun (по умолчанию latest)
# ${PORT} — порт приложения (по умолчанию 3000)
# ${START_CMD} — команда запуска (bun run src/index.ts / bun start)

# === Вариант A: с билд-шагом ===
FROM oven/bun:${BUN_VERSION} AS builder
WORKDIR /app
COPY package.json bun.lockb* ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM oven/bun:${BUN_VERSION}
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
EXPOSE ${PORT}
CMD ${START_CMD}

# === Вариант B: без билд-шага (раскомментируй и удали всё выше) ===
# FROM oven/bun:${BUN_VERSION}
# WORKDIR /app
# COPY package.json bun.lockb* ./
# RUN bun install --frozen-lockfile --production
# COPY . .
# EXPOSE ${PORT}
# CMD ${START_CMD}
