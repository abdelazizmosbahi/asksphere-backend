FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
COPY . .
COPY model_cache/hub /root/.cache/huggingface/hub
COPY model_cache/torch /root/.cache/torch/hub/checkpoints
ENV PORT=8000
EXPOSE 8000
CMD waitress-serve --port=$PORT --host=0.0.0.0 app:app