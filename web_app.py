#!/usr/bin/env python3
"""Flask web application for designing and printing Nelko P21 labels."""

import base64
import binascii
import io
import os

from flask import Flask, jsonify, render_template, request
from PIL import Image

from printer import NelkoPrinter, available_ports


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("A JSON request body is required")
    return data


def printer_from(data):
    device = str(data.get("device", "")).strip()
    if not device:
        raise ValueError("Select or enter a serial device")
    return NelkoPrinter(device)


def api_action(action):
    try:
        return jsonify({"ok": True, "result": action()})
    except (ConnectionError, TimeoutError, TypeError, ValueError, OSError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/ports")
def ports():
    return jsonify(
        {"ports": [{"device": device, "description": description} for device, description in available_ports()]}
    )


@app.post("/api/status")
def status():
    data = json_body()
    return api_action(lambda: str(printer_from(data).status()))


@app.post("/api/config")
def config():
    data = json_body()
    return api_action(lambda: str(printer_from(data).config()))


@app.post("/api/battery")
def battery():
    data = json_body()

    def read():
        level, charging = printer_from(data).battery()
        return {"level": level, "charging": charging}

    return api_action(read)


@app.post("/api/settings")
def settings():
    data = json_body()

    def apply():
        timeout = int(data.get("timeout"))
        beep = data.get("beep")
        if not isinstance(beep, bool):
            raise ValueError("Beep must be true or false")
        printer = printer_from(data)
        printer.set_timeout(timeout)
        printer.set_beep(beep)
        return "Printer settings applied"

    return api_action(apply)


@app.post("/api/self-test")
def self_test():
    data = json_body()

    def run():
        printer_from(data).self_test()
        return "Self-test requested"

    return api_action(run)


@app.post("/api/print")
def print_label():
    data = json_body()

    def run():
        encoded = str(data.get("image", ""))
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("The rendered label image is invalid") from exc
        try:
            with Image.open(io.BytesIO(raw)) as source:
                image = source.copy()
        except OSError as exc:
            raise ValueError("The rendered label is not a readable image") from exc
        density = int(data.get("density", 15))
        copies = int(data.get("copies", 1))
        printer_from(data).print_image(image, density, copies)
        return "Print sent"

    return api_action(run)


if __name__ == "__main__":
    app.run(host=os.environ.get("P21_HOST", "127.0.0.1"), port=int(os.environ.get("P21_PORT", "8080")))
