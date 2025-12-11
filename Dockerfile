# Use the official Apify Python base image
FROM apify/actor-python:3.11

# Copy all files to /usr/src/app (the working directory is set in the base image)
COPY . ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the actor
CMD ["python3", "src/main.py"]
