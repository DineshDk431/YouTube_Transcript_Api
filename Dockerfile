
# Python image to use.
FROM python:3.10-slim

# Allow statements and log messages to appear immediately in the Cloud Run logs
ENV PYTHONUNBUFFERED True

# Set the working directory to /app
ENV APP_HOME /app
WORKDIR $APP_HOME

# Copy the current directory contents into the container at /app
COPY . ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run main.py when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
