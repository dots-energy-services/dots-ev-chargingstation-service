FROM python:3.9.0
# If needed you can use the official python image (larger memory size)
#FROM python:3.9.0

RUN mkdir /app/
WORKDIR /app

COPY src/evservice ./
COPY requirements.txt ./
RUN pip install -r requirements.txt

ENTRYPOINT python3 evservice.py
