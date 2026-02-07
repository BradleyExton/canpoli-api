# Production image
FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Install dependencies (requirements.txt generated locally via: poetry export -f requirements.txt --without-hashes -o requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY canpoli ./canpoli
COPY alembic ./alembic
COPY alembic.ini .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "canpoli.main:app", "--host", "0.0.0.0", "--port", "8000"]
