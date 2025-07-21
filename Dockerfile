FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# Copy pre-downloaded model
COPY model_cache /root/.cache/huggingface/hub
ENV PORT=8000
EXPOSE 8000
CMD ["waitress-serve", "--port=$PORT", "app:app"]