FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download the model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
ENV PORT=8000
EXPOSE 8000
CMD ["waitress-serve", "--port=$PORT", "app:app"]