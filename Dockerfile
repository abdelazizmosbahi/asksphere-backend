FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu --timeout 1000 --retries 5
COPY . .
RUN mkdir -p /root/.cache/huggingface/hub /root/.cache/torch/hub/checkpoints
RUN ls -la model_cache/hub model_cache/torch/checkpoints || echo "model_cache directories not found"
COPY model_cache/hub/. /root/.cache/huggingface/hub/
COPY model_cache/torch/checkpoints/. /root/.cache/torch/hub/checkpoints/
ENV PORT=8000
EXPOSE 8000
CMD waitress-serve --port=$PORT --host=0.0.0.0 app:app