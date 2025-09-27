import os
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

# We no longer need the docker library. We will call the docker CLI directly.

@app.route('/execute', methods=['POST'])
def execute_code():
    data = request.json
    code = data.get('code', '')

    if not code:
        return jsonify({"error": "No code provided."}), 400

    # For security, we create a temporary file in a secure manner.
    # The 'with' block ensures the file is deleted even if errors occur.
    # We specify the '.cpp' suffix so the compiler recognizes it.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as temp_code_file:
        temp_code_file_path = temp_code_file.name
        temp_code_file.write(code)

    # We need the absolute path of the file to mount it into Docker.
    host_code_path = os.path.abspath(temp_code_file_path)
    # The path inside the container where the file will be mounted.
    container_code_path = "/app/main.cpp"

    image_name = "cpp-execution-env:latest"
    
    try:
        # This is the core of the new logic. We build a docker command as a list of arguments.
        # This is safer than a single string.
        docker_command = [
            "docker", "run",
            "--rm",  # Automatically remove the container when it exits
            "--user", "executionuser",  # Run as our non-root user
            "--network", "none",  # Disable networking for security
            "-v", f"{host_code_path}:{container_code_path}:ro", # Mount the code file as read-only
            image_name,
            # The command to run inside the container
            "sh", "-c", "g++ -std=c++17 main.cpp -o main.out && ./main.out"
        ]

        # We execute the command using subprocess.run
        # - capture_output=True grabs stdout and stderr.
        # - text=True decodes them as text.
        # - timeout=10 kills the process if it takes too long.
        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=10
        )

        return jsonify({
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Execution timed out after 10 seconds."}), 408
    except Exception as e:
        # Catch any other unexpected errors during the subprocess call.
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    finally:
        # This block ALWAYS runs, ensuring we clean up our temporary file.
        if os.path.exists(host_code_path):
            os.remove(host_code_path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

