FROM python:3.12-slim
WORKDIR /app
COPY ./streamlit/requirements.txt .
COPY ./streamlit .
RUN pip install -r requirements.txt
CMD [ "streamlit","run", "app.py" ]