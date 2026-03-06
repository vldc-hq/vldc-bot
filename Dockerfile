FROM golang:1.23-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /vldc-bot ./cmd/bot

FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata
COPY --from=builder /vldc-bot /vldc-bot

ENTRYPOINT ["/vldc-bot"]
