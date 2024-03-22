FROM python:3.12-slim
RUN apt-get -y update
RUN apt-get install -y --no-install-recommends ffmpeg

WORKDIR /usr/src/app
COPY requirements.txt .
COPY .env .
COPY src/ .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "./Main.py", "prod"]
