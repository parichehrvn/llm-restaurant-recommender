FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
COPY ./api .
RUN pip install --default-timeout=100 --retries 5 -r requirements.txt
RUN python -m spacy download en_core_web_sm
CMD ["uvicorn", "main:app","--host", "0.0.0.0", "--port", "8000"]