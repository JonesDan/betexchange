# Use the official Python image from Docker Hub
FROM --platform=linux/amd64 python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy Pipfile and Pipfile.lock from your repo to the working directory in the container
COPY Pipfile Pipfile.lock /app/

# Install pipenv
RUN pip install pipenv

# Install project dependencies using pipenv
RUN pipenv install --deploy --system

# Expose the port that the Flask app runs on
EXPOSE 5000

