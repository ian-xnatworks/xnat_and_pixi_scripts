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

# Label is a JSON string for XNAT's container service to parse
LABEL org.nrg.commands="[{\"name\": \"fnirs-qc-report-creator\", \"label\": \"fnirs-qc-report-creator\", \"description\": \"Amalgamate data and create a report based on fNIRS QC data\", \"version\": \"0.1.0\", \"schema-version\": \"1.0\", \"info-url\": \"https://github.com/ian-xnatworks/xnat_and_pixi_scripts\", \"container-name\": \"\", \"type\": \"docker\", \"index\": \"\", \"working-directory\": \"/usr/src/app\", \"command-line\": \"--u \$XNAT_USER --p \$XNAT_PASS --url \$XNAT_HOST #ELEMENT_ID# #ELEMENT_TYPE#\", \"override-entrypoint\": false, \"mounts\": [{\"name\": \"input-mount\", \"writable\": false, \"path\": \"/input\"}, {\"name\": \"output-mount\", \"writable\": true, \"path\": \"/fNIRS-qc-reports\"}], \"environment-variables\": {}, \"ports\": {}, \"inputs\": [{\"name\": \"element_id\", \"label\": null, \"description\": \"ID of the base XNAT element\", \"type\": \"string\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": \"#ELEMENT_ID#\", \"sensitive\": null, \"command-line-flag\": \"--be\", \"command-line-separator\": null, \"true-value\": null, \"false-value\": null, \"select-values\": [], \"multiple-delimiter\": null}, {\"name\": \"element_type\", \"label\": null, \"description\": \"The XNAT type of the element\", \"type\": \"string\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": \"#ELEMENT_TYPE#\", \"sensitive\": null, \"command-line-flag\": \"--type\", \"command-line-separator\": null, \"true-value\": null, \"false-value\": null, \"select-values\": [], \"multiple-delimiter\": null}], \"outputs\": [{\"name\": \"output\", \"description\": \"The output location for the final csv.\", \"mount\": \"output-mount\", \"required\": true}], \"xnat\": [{\"name\": \"project-level\", \"contexts\": [\"xnat:projectData\"], \"external-inputs\": [{\"name\": \"project\", \"label\": null, \"description\": \"Starting location when run from a project page.\", \"type\": \"Project\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": null, \"sensitive\": null, \"provides-value-for-command-input\": null, \"provides-files-for-command-mount\": null, \"via-setup-command\": null, \"user-settable\": null, \"load-children\": true}], \"derived-inputs\": [{\"name\": \"project-id\", \"label\": null, \"description\": \"XNAT Project ID\", \"type\": \"string\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": null, \"sensitive\": null, \"provides-value-for-command-input\": \"element_id\", \"provides-files-for-command-mount\": null, \"user-settable\": null, \"load-children\": false, \"derived-from-wrapper-input\": \"project\", \"derived-from-xnat-object-property\": \"id\", \"via-setup-command\": null, \"multiple\": false, \"parser\": null}], \"output-handlers\": []}, {\"name\": \"subject-level\", \"contexts\": [\"xnat:subjectData\"], \"external-inputs\": [{\"name\": \"subject\", \"label\": null, \"description\": \"Starting location when run from a subject page.\", \"type\": \"Subject\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": null, \"sensitive\": null, \"provides-value-for-command-input\": null, \"provides-files-for-command-mount\": null, \"via-setup-command\": null, \"user-settable\": null, \"load-children\": true}], \"derived-inputs\": [{\"name\": \"subject-id\", \"label\": null, \"description\": \"XNAT Subject ID\", \"type\": \"string\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": null, \"sensitive\": null, \"provides-value-for-command-input\": \"element_id\", \"provides-files-for-command-mount\": null, \"user-settable\": null, \"load-children\": false, \"derived-from-wrapper-input\": \"subject\", \"derived-from-xnat-object-property\": \"id\", \"via-setup-command\": null, \"multiple\": false, \"parser\": null}], \"output-handlers\": []}, {\"name\": \"experiment-level\", \"contexts\": [\"xnat:imageSessionData\"], \"external-inputs\": [{\"name\": \"session\", \"label\": null, \"description\": \"Starting location when run from a experiment page.\", \"type\": \"Session\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": null, \"sensitive\": null, \"provides-value-for-command-input\": null, \"provides-files-for-command-mount\": null, \"via-setup-command\": null, \"user-settable\": null, \"load-children\": true}], \"derived-inputs\": [{\"name\": \"session-id\", \"label\": null, \"description\": \"XNAT Session ID\", \"type\": \"string\", \"matcher\": null, \"default-value\": null, \"required\": true, \"replacement-key\": null, \"sensitive\": null, \"provides-value-for-command-input\": \"element_id\", \"provides-files-for-command-mount\": null, \"user-settable\": null, \"load-children\": false, \"derived-from-wrapper-input\": \"session\", \"derived-from-xnat-object-property\": \"id\", \"via-setup-command\": null, \"multiple\": false, \"parser\": null}], \"output-handlers\": []}], \"runtime\": \"\", \"ipc-mode\": \"\", \"network\": \"\", \"container-labels\": {}, \"generic-resources\": {}, \"ulimits\": {}}]"
