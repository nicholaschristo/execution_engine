import docker
import platform

print("Attempting to connect to Docker...")

try:
    client = None
    # Check if the operating system is Windows
    if platform.system() == "Windows":
        print("Detected Windows. Attempting to connect via named pipe...")
        try:
            # On Windows, the Docker daemon often listens on a named pipe.
            # This connects to it directly, bypassing environment variables.
            client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
            # A quick ping confirms the connection is live.
            client.ping()
            print(" -> Connection successful via named pipe.")
        except Exception as e:
            print(f" -> Named pipe connection failed: {e}")
            print(" -> Falling back to default connection method...")
            # If the named pipe fails for some reason, try the default method again.
            client = docker.from_env()
    else:
        # For macOS and Linux, the default from_env() usually works correctly.
        print("Detected non-Windows OS. Using default connection method...")
        client = docker.from_env()

    # If the connection succeeds, we'll try to do something simple
    print("\n✅ Successfully connected to Docker!")
    
    print("\nListing available images:")
    images = client.images.list()
    if not images:
        print(" -> No images found.")
    else:
        for image in images:
            # image.tags can be empty, so handle that case
            if image.tags:
                print(f" -> {image.tags[0]}")
            else:
                print(" -> <untagged image>")

except Exception as e:
    print("\n❌ Failed to connect to Docker from Python.")
    print("This is the root cause of the problem in app.py.")
    print("\n--- Error Details ---")
    print(e)
    print("---------------------")

