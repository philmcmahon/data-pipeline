import subprocess
import time

import requests

VLLM_BASE_URL = "http://127.0.0.1:8000"

_vllm_process = None


def stop_vllm_server():
    global _vllm_process
    if _vllm_process is not None:
        print("Stopping existing vllm server...")
        _vllm_process.terminate()
        try:
            _vllm_process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            _vllm_process.kill()
            _vllm_process.wait()
        _vllm_process = None


def start_vllm_server(model, extra_args=None):
    global _vllm_process
    stop_vllm_server()
    cmd = ["vllm", "serve", model, "--host", "127.0.0.1", "--port", "8000"]
    if extra_args:
        cmd.extend(extra_args)
    print(f"Starting vllm server: {' '.join(cmd)}")
    _vllm_process = subprocess.Popen(cmd)

    # Wait for server to be ready and model to be loaded
    for _ in range(120):
        try:
            r = requests.get(f"{VLLM_BASE_URL}/v1/models", timeout=2)
            if r.status_code == 200:
                models = r.json().get("data", [])
                if any(m.get("id") == model for m in models):
                    print("vllm server is ready")
                    return
        except requests.ConnectionError:
            pass
        time.sleep(5)
    raise RuntimeError("vllm server failed to start within timeout")
