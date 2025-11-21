FROM python:3.12-slim

WORKDIR /app

# Copy your script into the image
COPY rss.py .

# If you have dependencies:
# COPY requirements.txt .
# RUN pip install -r requirements.txt

CMD ["python", "rss.py"]
