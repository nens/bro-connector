# Use the official Python runtime image
FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install GDAL and other dependencies
RUN apt-get update

RUN apt-get -y install gdal-bin libgdal-dev python3-gdal build-essential python3-dev

RUN apt-get -y install git

# Create the app directory
RUN mkdir /app

# Set the working directory inside the container
WORKDIR /app

# Set environment variables
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Create venv
RUN uv venv

# Upgrade pip
RUN uv pip install --upgrade pip

# Copy the Django project  and install dependencies
COPY requirements.txt  /app/

# run this command to install all dependencies
RUN uv pip install --no-cache-dir -r requirements.txt

# Copy the Django project to the container
COPY ./bro_connector /app/

# Expose the Django port
EXPOSE 8000

RUN pwd
RUN ls

RUN cd /app/

RUN pwd

# Run Django’s development server
CMD ["uv", "run", "manage.py", "runserver"]
