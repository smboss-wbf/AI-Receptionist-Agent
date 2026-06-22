# Builds livekit-sip from source.
# No prebuilt binary or package exists for this — it must be compiled,
# and requires opus/soxr/opusfile as native (non-Go) audio libraries.

FROM golang:1.22-bookworm AS builder

# Native audio library dependencies for the cgo-based opus/soxr bindings
RUN apt-get update && apt-get install -y \
    git \
    pkg-config \
    libopus-dev \
    libopusfile-dev \
    libsoxr-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Clone the official livekit/sip repo at build time
RUN git clone --depth 1 https://github.com/livekit/sip.git .

# Compile the livekit-sip binary
RUN go build -o livekit-sip ./cmd/livekit-sip

# --- Final, smaller runtime image ---
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libopus0 \
    libopusfile0 \
    libsoxr0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/livekit-sip .

EXPOSE 5060/udp
EXPOSE 5060/tcp

CMD ["./livekit-sip", "--config", "/app/config.yaml"]
