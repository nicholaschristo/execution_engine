# app.py

import os
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- MANUAL CORS IMPLEMENTATION (Fixes Frontend Errors) ---
# This ensures CORS headers are sent reliably for your frontend.

FRONTEND_ORIGIN = 'http://localhost:3000'

@app.before_request
def before_request_func():
    # Handle the OPTIONS preflight request explicitly
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        
        # Manually set headers for the OPTIONS response (CRITICAL for CORS)
        resp.headers['Access-Control-Allow-Origin'] = FRONTEND_ORIGIN
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Access-Control-Max-Age'] = '86400' # Cache preflight response
        return resp

@app.after_request
def after_request_func(response):
    # Manually set header for the actual POST response
    response.headers['Access-Control-Allow-Origin'] = FRONTEND_ORIGIN
    return response

# --------------------------------------------------------


@app.route('/execute', methods=['OPTIONS', 'POST']) 
def execute_code():
    # Only proceed with execution logic on a POST request
    if request.method == 'POST':
        try:
            # 1. Input Validation
            if not request.is_json:
                return jsonify({"error": "Missing JSON in request body"}), 400
            
            data = request.get_json()
            code = data.get('code', '')

            if not code:
                return jsonify({"error": "No code provided."}), 400

            # 2. Prepare Temporary File
            # This creates and writes the C++ code to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as temp_code_file:
                temp_code_file_path = temp_code_file.name
                temp_code_file.write(code)

            host_code_path = os.path.abspath(temp_code_file_path)
            container_code_path = "/app/main.cpp"
            image_name = "cpp-execution-env:latest"
            
            # 3. Construct and Run Docker Command
            docker_command = [
                "docker", "run",
                "--rm",
                "--user", "executionuser",
                "--network", "none",
                "-v", f"{host_code_path}:{container_code_path}:ro", 
                image_name,
                # Command to run inside container: Compile (g++) and Execute (./main.out)
                "sh", "-c", "g++ -std=c++17 main.cpp -o main.out && ./main.out"
            ]

            result = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                timeout=10
            )

            # 4. Return Output
            return jsonify({
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            })

        except subprocess.TimeoutExpired:
            return jsonify({
                "exit_code": -1,
                "stdout": "",
                "stderr": "Execution timed out after 10 seconds."
            }), 408
            
        except Exception as e:
            # Catch file, Docker execution, or other unexpected errors
            return jsonify({
                "exit_code": -1,
                "stdout": "",
                "stderr": f"An unexpected server error occurred: {str(e)}"
            }), 500
            
        finally:
            # 5. Cleanup
            # This MUST run to remove the temporary file regardless of success or failure.
            if os.path.exists(host_code_path):
                os.remove(host_code_path)
    
    # This route will handle the OPTIONS preflight (handled by @before_request)
    # and ensures POST is handled above.
    return 'Method not allowed', 405


if __name__ == '__main__':
    # Running on 0.0.0.0 ensures it's accessible from outside the container 
    # if you were running Flask in Docker, but it's good practice for ngrok too.
    # Port 5000 is the default—ensure ngrok targets this port.
    app.run(host='0.0.0.0', port=5000, debug=True)