FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install FlightRadarAPI requests
CMD ["python", "main.py"]