import pytest
import httpx
import subprocess
import time
import os
import sys

# Add project root to sys.path to allow importing weather_mcp.main
# This assumes tests are run from the directory containing weather_mcp or project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

# Import mcp object after sys.path modification.
# This is primarily to ensure that the mcp object instance that gets patched in main.py
# is the one we intend to test. However, for subprocess testing, this import isn't strictly
# necessary for the test execution itself but good for static analysis or if we ever directly use it.
try:
    from weather_mcp import main as weather_main_module
except ImportError:
    weather_main_module = None # Allows tests to run if main module has issues not related to these tests

TEST_PORT = 3400 # Using a different port for tests
BASE_URL = f"http://localhost:{TEST_PORT}"
HEALTH_CHECK_URL = f"{BASE_URL}/mcp/health_check"
INFO_URL = f"{BASE_URL}/mcp/info"
DOCS_URL = f"{BASE_URL}/docs"
OPENAPI_URL = f"{BASE_URL}/openapi.json"

# Example protected tool endpoint (assuming weather plugin is mounted at /weather)
PROTECTED_TOOL_URL = f"{BASE_URL}/mcp/weather.get_weather"

VALID_TOKEN = "test_secret_token_12345"
INVALID_TOKEN = "invalid_token_67890"

@pytest.fixture(scope="module")
def mcp_server_process():
    """
    Starts the MCP server as a subprocess for module-scoped testing.
    Ensures MCP_SHARED_SECRET is set for the subprocess.
    """
    env = os.environ.copy()
    env["MCP_SHARED_SECRET"] = VALID_TOKEN
    env["MCP_TRANSPORT_MODE"] = "streamable-http" # Use streamable-http for easier testing
    env["HTTP_PORT"] = str(TEST_PORT)
    # Ensure logs from the server don't clutter test output too much, or are identifiable
    env["LOG_LEVEL"] = "WARNING"

    # Path to main.py, assuming tests/test_auth.py is in weather_mcp/tests/
    main_py_path = os.path.join(os.path.dirname(__file__), "..", "main.py")

    process = None
    try:
        # Start the server process
        # Using sys.executable to ensure the same Python interpreter is used
        process = subprocess.Popen(
            [sys.executable, main_py_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for the server to be ready
        max_wait_time = 20  # seconds
        start_time = time.time()
        server_ready = False
        while time.time() - start_time < max_wait_time:
            try:
                with httpx.Client() as client:
                    response = client.get(HEALTH_CHECK_URL, timeout=1)
                if response.status_code == 200:
                    server_ready = True
                    print(f"Server ready at {HEALTH_CHECK_URL}")
                    break
            except httpx.RequestError as e:
                # print(f"Server not ready yet, retrying... ({e})")
                time.sleep(0.5) # Wait a bit before retrying
            if process.poll() is not None: # Process died
                print("Server process died before becoming ready.")
                break

        if not server_ready:
            stdout, stderr = process.communicate()
            print("Server stdout:\n", stdout.decode(errors='replace'))
            print("Server stderr:\n", stderr.decode(errors='replace'))
            raise RuntimeError(f"MCP server failed to start on port {TEST_PORT} within {max_wait_time}s.")

        yield process # Provide the process to the tests

    finally:
        if process:
            print(f"Terminating server process (PID: {process.pid})...")
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5) # Wait for termination
                print("Server stdout (on termination):\n", stdout.decode(errors='replace'))
                print("Server stderr (on termination):\n", stderr.decode(errors='replace'))
            except subprocess.TimeoutExpired:
                print(f"Server process (PID: {process.pid}) did not terminate gracefully, killing.")
                process.kill()
                stdout, stderr = process.communicate()
                print("Server stdout (on kill):\n", stdout.decode(errors='replace'))
                print("Server stderr (on kill):\n", stderr.decode(errors='replace'))
            print("Server process terminated.")


# Test cases
@pytest.mark.usefixtures("mcp_server_process")
def test_protected_route_valid_token():
    headers = {"Authorization": f"Bearer {VALID_TOKEN}"}
    payload = {"tool": "weather.get_weather", "args": {"city": "TestCity"}} # Assuming this tool exists
    with httpx.Client() as client:
        response = client.post(PROTECTED_TOOL_URL, json=payload, headers=headers)

    # Depending on the actual tool's success response.
    # If the tool runs successfully, it should not be a 401/403.
    # A successful tool call in FastMCP usually returns 200 with the tool's output.
    # Here, we primarily care that it's not an auth error.
    # The dummy weather plugin might error if API key is not set, but that's not an auth error.
    assert response.status_code != 401
    assert response.status_code != 403
    # If a dummy API key is not configured for tests, the weather tool might return an error,
    # e.g. 500 or a specific MCP error structure. For this test, we focus on not getting 401.
    # A more robust check would be if the actual tool logic executed,
    # but that depends on the tool and its own error handling.
    # For now, if it's not 401, auth was bypassed.
    # Let's assume a valid, non-auth error (e.g., tool error) might be 200 (with error in JSON) or 500.
    # The key is that auth itself passed.
    if response.status_code == 200:
        print("Protected route response (valid token):", response.json())
    else:
        print(f"Protected route response (valid token, non-200 OK): {response.status_code}", response.text)


@pytest.mark.usefixtures("mcp_server_process")
def test_protected_route_invalid_token():
    headers = {"Authorization": f"Bearer {INVALID_TOKEN}"}
    payload = {"tool": "weather.get_weather", "args": {"city": "TestCity"}}
    with httpx.Client() as client:
        response = client.post(PROTECTED_TOOL_URL, json=payload, headers=headers)
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

@pytest.mark.usefixtures("mcp_server_process")
def test_protected_route_no_token():
    payload = {"tool": "weather.get_weather", "args": {"city": "TestCity"}}
    with httpx.Client() as client:
        response = client.post(PROTECTED_TOOL_URL, json=payload) # No headers
    assert response.status_code == 401
    assert "Missing Authorization header" in response.json()["detail"]

@pytest.mark.usefixtures("mcp_server_process")
def test_exempt_route_health_check_no_token():
    with httpx.Client() as client:
        response = client.get(HEALTH_CHECK_URL)
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.usefixtures("mcp_server_process")
def test_exempt_route_info_no_token():
    with httpx.Client() as client:
        response = client.get(INFO_URL)
    assert response.status_code == 200
    # The info endpoint returns a JSON string as text, not a direct JSON response
    # So, we check if 'status' and 'healthy' are in the text.
    assert '"status": "healthy"' in response.text

@pytest.mark.usefixtures("mcp_server_process")
def test_exempt_route_docs_no_token():
    with httpx.Client(follow_redirects=True) as client: # Follow redirects for /docs to /docs/
        response = client.get(DOCS_URL)
    assert response.status_code == 200
    assert "<title>FastAPI - Swagger UI</title>" in response.text # Check for Swagger UI content

@pytest.mark.usefixtures("mcp_server_process")
def test_exempt_route_openapi_no_token():
    with httpx.Client() as client:
        response = client.get(OPENAPI_URL)
    assert response.status_code == 200
    assert "openapi" in response.json()
    assert "WeatherServer" in response.json()["info"]["title"]

# End of actual test code. Problematic comments that were here have been removed.
