# Use a minimal base image to reduce attack surface
FROM gcc:12.2

# Set up a non-root user for security
RUN useradd -ms /bin/bash executionuser
USER executionuser

# Create a working directory
WORKDIR /app

# The container will start and wait for a command.
# The `app.py` script will provide the command to compile and run the code.
CMD ["/bin/bash"]
