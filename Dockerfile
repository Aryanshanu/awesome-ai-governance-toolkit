# Multi-stage Dockerfile — Awesome AI Governance Toolkit
# Stage 1: dependency builder (keeps final image lean)
FROM python:3.13-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: runtime image
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="Awesome AI Governance Toolkit"
LABEL org.opencontainers.image.description="Runtime firewall and cryptographic audit ledger for enterprise AI"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Pre-build the ChromaDB/sentence-transformers index at image build time
# (optional — comment out to defer to first runtime request)
# RUN python -c "from src.rag import build_index; build_index()"

# Expose both service ports
EXPOSE 8000 8501

# Health check against the FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start API server + Streamlit dashboard in parallel
CMD ["sh", "-c", \
  "uvicorn src.main:app --host 0.0.0.0 --port 8000 & \
   streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"]
