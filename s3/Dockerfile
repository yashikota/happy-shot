FROM golang:1.23-bookworm AS build
ENV TZ=Asia/Tokyo

ENV CGO_ENABLED=0
ENV GOOS=linux
ENV GOARCH=amd64

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN go build -o /bin/main -ldflags="-s -w" .

# ==============================================

FROM gcr.io/distroless/static-debian12 AS deploy
ENV TZ=Asia/Tokyo

COPY --from=build /bin/main /main

EXPOSE 5000
USER nonroot:nonroot

CMD ["/main"]
