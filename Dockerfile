FROM python:3-slim
LABEL org.opencontainers.image.authors="13583702+LittleJake@users.noreply.github.com"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./report.py" ]
