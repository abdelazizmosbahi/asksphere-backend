FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu --timeout 1000
COPY . .
RUN mkdir -p /root/.cache/huggingface/hub /root/.cache/torch/hub/checkpoints
COPY model_cache/hub/. /root/.cache/huggingface/hub/
COPY model_cache/torch/checkpoints/. /root/.cache/torch/hub/checkpoints/
COPY .env .
EXPOSE 5000
CMD ["waitress-serve", "--port=5000", "--host=0.0.0.0", "app:app"]