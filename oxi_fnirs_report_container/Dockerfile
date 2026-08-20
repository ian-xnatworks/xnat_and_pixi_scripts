FROM python:3.12-slim

# Update the package list and upgrade installed packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Update pip and setuptools to the latest version
RUN pip install --no-cache-dir --upgrade pip setuptools

# Update pip and setuptools to the latest version
RUN pip install --no-cache-dir --upgrade pip setuptools

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set the working directory and copy requirements
WORKDIR /usr/src/app
COPY requirements.txt ./

# Install the requirements and set the permissions
RUN pip install --no-cache-dir -r requirements.txt && \
    chown -R appuser:appgroup /usr/src/app && \
    rm requirements.txt

# Copy the source code
COPY copy_reports ./

# Update the PYTHONPATH with the source code
ENV PYTHONPATH=${PYTHONPATH}:/usr/src/app:/usr/src/app/copy_reports
ENV PYTHONUNBUFFERED=1

# Switch to the non-root user
USER appuser

# Set the entrypoint and command
ENTRYPOINT [ "python", "copy_reports/oxi_fnirs_report_creator.py" ]
CMD ["--help"]

#need to add the command here