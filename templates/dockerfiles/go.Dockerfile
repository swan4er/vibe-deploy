# Go Dockerfile — multi-stage build
# Агент: подставь значения переменных перед использованием.
# ${GO_VERSION} — версия Go (по умолчанию 1.22)
# ${PORT} — порт приложения (по умолчанию 8080)
# ${MAIN_PATH} — путь к main.go (по умолчанию .)

FROM golang:${GO_VERSION}-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server ${MAIN_PATH}

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/server .
EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:${PORT}/health || exit 1
CMD ["./server"]
