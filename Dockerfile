# Uses python 3 as the base image for the Docker container
FROM python:3.11-slim

#
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container to /kavarna
WORKDIR /kavarna

# Copy the requirements.txt file to the working directory and install the dependencies specified in it using pip.
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the entire contents of the current directory to the working directory in the container.
COPY . .

# Expose port 8000 to allow access to the Django development server from outside the container.
EXPOSE 8000

# Set the default command to run the Django development server when the container starts.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]