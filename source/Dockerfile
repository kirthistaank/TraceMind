FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python libraries
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy all project code into the container
COPY . .

# Expose the standard Hugging Face Space port
EXPOSE 7860

# Configure health checks for the container
HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health

# Command to run your app on port 7860
ENTRYPOINT ["streamlit", "run", "source/streamlit_ui.py", "--server.port=7860", "--server.address=0.0.0.0"]
