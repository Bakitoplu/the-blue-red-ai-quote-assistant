FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app
COPY the_blue_red_candidate_case_dataset /dataset
ENV DATASET_DIR=/dataset
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
