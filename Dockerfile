FROM python:3-slim
MAINTAINER LittleJake https://github.com/LittleJake/

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./report.py" ]
