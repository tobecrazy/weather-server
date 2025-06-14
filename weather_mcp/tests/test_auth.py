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

# To run these tests:
# Ensure `weather_mcp` directory is in PYTHONPATH or run from parent of `weather_mcp`
# Example: `python -m pytest weather_mcp/tests/test_auth.py`
# Ensure OPENWEATHERMAP_API_KEY is either not set or is a dummy for tests,
# as the weather tool itself might fail if it expects a real key.
# The tests here focus on auth, not the tool's full functionality.
# Set LOG_LEVEL=DEBUG for the server if more detailed logs are needed during testing.
# e.g. env["LOG_LEVEL"] = "DEBUG" in the fixture.
# The `PROJECT_ROOT` and `sys.path.insert` are attempts to make test discovery and imports robust.
# Depending on how pytest is called, this might need adjustment.
# If run with `pytest` from the project root containing `weather_mcp` folder, it should work.
# Example: If project is `my_project/weather_mcp/`, run `pytest` from `my_project/`.
# Or `python -m pytest` from `my_project/`.
# The current setup assumes `weather_mcp/tests/test_auth.py` and `weather_mcp/main.py`.
# So, running `pytest` from the directory containing `weather_mcp` should work.
# If `weather_mcp` is the root, then `pytest tests/test_auth.py`.
# The `sys.path.insert` is for `python -m pytest weather_mcp/tests/test_auth.py` from one level up.

# A note on `test_protected_route_valid_token`:
# The test currently asserts `response.status_code != 401` and `!= 403`.
# This is because the actual weather tool might fail (e.g., due to missing API key for OpenWeatherMap)
# leading to a 500 error or a 200 OK with an error message in the JSON payload from the tool.
# The primary goal of this test is to ensure authentication passed, not that the tool itself worked perfectly.
# If a dummy OpenWeatherMap API key is set in the test environment, the tool might respond differently.
# For true end-to-end testing of the tool, it would need its own dedicated tests with proper mocking or API key setup.
# This test focuses on the *authentication layer*.
# If the auth passes, the request reaches the tool. The tool's response is secondary here.
# The server logs (captured by the fixture) can be helpful in diagnosing issues.
# The `weather_main_module` import is a bit of a placeholder; for subprocess tests, it's not strictly used at runtime
# by the test functions themselves, but linters/IDEs might expect it.
# The server is run entirely out-of-process.
# The `PYTHONPATH` adjustment is crucial for `python -m pytest ...` from a root directory.
# If `pytest` is run directly from `weather_mcp` (e.g. `cd weather_mcp; pytest tests/test_auth.py`),
# then `sys.path` might be okay without the manipulation, but it's safer to be explicit.
# The current `PROJECT_ROOT` calculation assumes `weather_mcp/tests/test_auth.py`.
# If `weather_mcp` is the root, then `PROJECT_ROOT` should be `os.path.dirname(__file__)`
# and `main_py_path` would be `os.path.join(PROJECT_ROOT, "..", "main.py")` - no, it would be `os.path.join(PROJECT_ROOT, "main.py")`.
# Let's assume the structure is `project_root/weather_mcp/tests/test_auth.py` and `project_root/weather_mcp/main.py`.
# So, `PROJECT_ROOT` being `project_root` is correct for `from weather_mcp import main`.
# And `main_py_path` is `project_root/weather_mcp/main.py`.
# The current paths:
# `os.path.dirname(__file__)` is `project_root/weather_mcp/tests`
# `os.path.join(os.path.dirname(__file__), '..')` is `project_root/weather_mcp`
# `os.path.join(os.path.dirname(__file__), '..', '..')` is `project_root` -> CORRECT for PROJECT_ROOT
# `main_py_path = os.path.join(os.path.dirname(__file__), "..", "main.py")` -> `project_root/weather_mcp/tests/../main.py` which is `project_root/weather_mcp/main.py` -> CORRECT for main_py_path

# To make the tests runnable with `python -m pytest` from the directory containing the `weather_mcp` folder:
# (e.g. if `weather_mcp` is a sub-directory of your project root `my_weather_project`)
# `my_weather_project/weather_mcp/tests/test_auth.py`
# `my_weather_project/weather_mcp/main.py`
# Then `cd my_weather_project`
# `python -m pytest` or `python -m pytest weather_mcp/tests/test_auth.py`
# The `sys.path.insert(0, PROJECT_ROOT)` where `PROJECT_ROOT` points to `my_weather_project` helps Python find `weather_mcp.main`.
# The `PYTHONPATH` could also be set externally.
# The current `PROJECT_ROOT` setup is for this scenario.
# If `weather_mcp` *is* the root of the project, then `PROJECT_ROOT` would be `os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))`
# and `sys.path.insert(0, PROJECT_ROOT)` would add `weather_mcp` to path, allowing `import main` (but not `weather_mcp.main`).
# So the current structure is fine for `from weather_mcp.main import mcp` if `weather_mcp` is a package.
# Given the `PYTHONPATH` manipulation, it should generally work if the tests are discovered.

# Final check on paths for `mcp_server_process` fixture:
# `main_py_path` is `weather_mcp/main.py` relative to the project root.
# If `pytest` is run from project root, `os.getcwd()` is project root.
# `[sys.executable, "weather_mcp/main.py"]` might be more direct if `pytest` CWD is project root.
# The current `main_py_path` is absolute, which is robust.

# The test for `test_protected_route_valid_token` expects a POST request to `/mcp/weather.get_weather`.
# The `weather.py` plugin defines `weather_mcp = FastMCP(name="WeatherPlugin")` and `@weather_mcp.tool() async def get_weather(...)`.
# In `main.py`, `mcp.mount("weather", weather_mcp)`.
# So the tool name is `weather.get_weather`. The default MCP prefix is `/mcp`.
# Thus, the URL is indeed `/mcp/weather.get_weather`.

# The health check endpoint `/mcp/health_check` is defined as `@mcp.tool() async def health_check()`.
# So its URL is `/mcp/health_check`.
# The info endpoint `/mcp/info` is from `TextResource(uri="resource://mcp/info", ...)` and `mcp.add_resource`.
# `FastMCP` serves these at `/mcp/info`.
# These paths seem correct.

# The `test_protected_route_valid_token` check `assert response.status_code != 401` is a bit weak.
# If the dummy API key is not set, the weather tool itself (plugins/weather.py) might raise an error,
# which could result in a 500 or a 200 OK with an error structure.
# For example, if `plugins/weather.py` has: `raise HTTPException(status_code=400, detail="API key not configured")`
# this would be a 400. If it returns `{"error": "API key missing"}` with status 200, that's also possible.
# The key is that authentication was successful. A more specific check would be ideal if we
# could guarantee a specific non-auth error or success code from the tool under test conditions.
# For now, not 401/403 is the primary check for passed authentication.
# The server logs printed on fixture teardown will be helpful.
# The `print` statements in the test can also be useful when running with `pytest -s`.
# Added `stdout=subprocess.PIPE, stderr=subprocess.PIPE` to Popen.
# Modified fixture teardown to print server logs for better debugging.
# Increased server startup timeout to 20s.
# Added check for `process.poll()` during startup loop.
# Made `LOG_LEVEL` for the server `WARNING` to reduce noise, can be changed to `DEBUG` if needed.
# Added check for `DOCS_URL` and `OPENAPI_URL` to be exempt.
# Corrected `INFO_URL` check: it returns text, not JSON directly.
# Added `follow_redirects=True` for `/docs` as FastAPI redirects `/docs` to `/docs/`.
# The `weather_main_module` import is mostly for linters, not strictly needed for subprocess tests.
# The `sys.path.insert` is more critical if tests were importing and using parts of `main.py` directly
# (e.g. for unit tests not involving a subprocess). For subprocess, it's less critical but good practice
# for consistency if other tests in the suite might do direct imports.
# The paths in `PROJECT_ROOT` and `main_py_path` are robust for typical project structures.
# Example: Project structure `your_project_root/weather_mcp/{main.py, tests/test_auth.py, ...}`
# Running `pytest` from `your_project_root` should work.
# Running `python -m pytest weather_mcp/tests/test_auth.py` from `your_project_root` should also work.
# The `PYTHONPATH` should be set to `your_project_root` or `sys.path` should contain it.
# The `sys.path.insert(0, PROJECT_ROOT)` line handles this for the `python -m pytest ...` case.
# If pytest is run as `pytest` from project root, it usually adds project root to sys.path by default.
# The fixture timeout for server startup is now 20 seconds.
# The payload for the protected route POST is `{"tool": "weather.get_weather", "args": {"city": "TestCity"}}`.
# This is the correct format for FastMCP tool calls.
# The URL `PROTECTED_TOOL_URL` is `f"{BASE_URL}/mcp/weather.get_weather"`. This is also correct.
# The `AuthMiddleware` in `main.py` exempts `/mcp/health_check` and `/mcp/info`.
# It also exempts `/openapi.json`, `/docs`, `/redoc`.
# The tests cover these exemptions.
# The `test_protected_route_valid_token` will pass auth. The tool `weather.get_weather` might still fail
# if `OPENWEATHERMAP_API_KEY` is not set in the environment for the subprocess.
# The `plugins/weather.py` has logic for missing API key.
# It logs a warning and then tries to make the API call, which will fail.
# OpenWeatherMap API returns 401 if API key is missing/invalid.
# The `get_weather_data` function in `plugins/weather.py` catches `requests.exceptions.RequestException`
# and `KeyError` (if response structure is bad) and then raises `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, ...)`
# or `HTTPException(status_code=status.HTTP_400_BAD_REQUEST, ...)`.
# So, if auth passes but API key is missing, we expect a 400 or 503 from the tool, not 200.
# This means `assert response.status_code != 401` is good. If it's 400/503, it means auth worked.
# This is fine for an auth test.
# The `test_protected_route_valid_token` could be more specific if we mock the weather API or ensure a valid dummy key is used
# that results in a predictable tool outcome (e.g., a specific error or success).
# However, for *just* testing the auth wrapper, knowing it didn't return 401/403 is the core.
# The server process's stdout/stderr are now captured and printed, which will show any errors from the tool itself.
# This should be sufficient.Okay, I've created the `weather_mcp/tests/test_auth.py` file with the necessary imports, fixtures, and test cases.

The key aspects are:
-   **`pytest` and `httpx`**: Assumed to be installed from the updated `requirements.txt`.
-   **Server Fixture (`mcp_server_process`)**:
    -   Runs `weather_mcp/main.py` as a subprocess.
    -   Sets environment variables: `MCP_SHARED_SECRET` (to a known `VALID_TOKEN`), `MCP_TRANSPORT_MODE="streamable-http"`, `HTTP_PORT` (to `3400`), and `LOG_LEVEL="WARNING"`.
    -   Waits for the server to become healthy by polling `/mcp/health_check`.
    -   Yields the subprocess and handles its termination, printing server logs for debugging.
-   **Test Cases**:
    -   `test_protected_route_valid_token`: Accesses `/mcp/weather.get_weather` with a valid token. Asserts the status code is *not* 401 or 403, indicating authentication passed (the tool itself might error due to API key issues, but that's a separate concern for this auth test).
    -   `test_protected_route_invalid_token`: Uses an invalid token, expects 401.
    -   `test_protected_route_no_token`: Provides no token, expects 401.
    -   `test_exempt_route_health_check_no_token`: Accesses `/mcp/health_check` without a token, expects 200.
    -   `test_exempt_route_info_no_token`: Accesses `/mcp/info` without a token, expects 200.
    -   `test_exempt_route_docs_no_token`: Accesses `/docs` without a token, expects 200.
    -   `test_exempt_route_openapi_no_token`: Accesses `/openapi.json` without a token, expects 200.
-   **Path Management**: Includes logic to adjust `sys.path` to help Python find the `weather_mcp.main` module, making the tests more runnable from different working directories or with different `pytest` invocation styles.

The tests are designed to be run with a command like `python -m pytest weather_mcp/tests/test_auth.py` from the project root (the directory containing the `weather_mcp` folder).

The next step would be to actually run these tests in the environment, but I can only prepare the files. I've included detailed comments in the test file regarding execution and potential issues.

I'll now submit the report for this subtask.
