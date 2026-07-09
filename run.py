"""Run the app locally with a public ngrok tunnel.

Starts an ngrok tunnel on the reserved static domain, then runs the Flask
app. The tunnel is torn down automatically when the app stops (Ctrl+C,
normal exit, or an unhandled error).
"""
import atexit
import signal
import subprocess
import sys

from waitress import serve

from app import app, init_db

PORT = 5000
NGROK_STATIC_DOMAIN = "goatskin-zodiac-entryway.ngrok-free.dev"

_ngrok_process = None


def start_ngrok():
    global _ngrok_process
    try:
        _ngrok_process = subprocess.Popen(
            ["ngrok", "http", f"--url={NGROK_STATIC_DOMAIN}", str(PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(
            "ngrok executable not found on PATH. Install ngrok or add it to PATH; "
            "continuing without a public tunnel.",
            file=sys.stderr,
        )
        return
    print(f"ngrok tunnel starting -> https://{NGROK_STATIC_DOMAIN}")


def stop_ngrok():
    global _ngrok_process
    if _ngrok_process is None or _ngrok_process.poll() is not None:
        return
    _ngrok_process.terminate()
    try:
        _ngrok_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _ngrok_process.kill()
        _ngrok_process.wait()
    print("ngrok tunnel stopped.")
    _ngrok_process = None


def _handle_signal(signum, frame):
    stop_ngrok()
    sys.exit(0)


atexit.register(stop_ngrok)
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    start_ngrok()
    init_db(app)
    try:
        # waitress instead of app.run(): Flask's built-in server is
        # explicitly not meant for serving requests from the internet,
        # which is what this becomes once ngrok exposes it publicly.
        serve(app, host="127.0.0.1", port=PORT, threads=8)
    finally:
        stop_ngrok()
