#!/usr/bin/env python3
"""Launch the Nelko P21 GUI or use its printer features from the command line."""

import argparse

from PIL import Image

from printer import DEFAULT_DEVICE, NelkoPrinter, available_ports


def parse_bool(value):
    normalized = value.lower()
    if normalized in ("true", "yes", "on", "1"):
        return True
    if normalized in ("false", "no", "off", "0"):
        return False
    raise argparse.ArgumentTypeError("expected true/false, yes/no, on/off, or 1/0")


def positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(
        description="Open the Nelko P21 label editor or perform a printer command."
    )
    parser.add_argument("--gui", action="store_true", help="Open the label editor")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Serial port, such as COM5 or /dev/rfcomm0")
    parser.add_argument("--list-devices", action="store_true", help="List serial ports")
    parser.add_argument("--image", help="Print an image directly")
    parser.add_argument("--density", type=int, choices=range(1, 16), default=15)
    parser.add_argument("--copies", type=positive_int, default=1)
    parser.add_argument("--status", action="store_true", help="Read printer status")
    parser.add_argument("--config", action="store_true", help="Read printer configuration")
    parser.add_argument("--battery", action="store_true", help="Read battery status")
    parser.add_argument("--timeout", type=int, choices=(0, 15, 30, 60))
    parser.add_argument("--beep", type=parse_bool, metavar="BOOLEAN")
    parser.add_argument("--selftest", action="store_true", help="Run the printer self-test")
    return parser


def launch_gui():
    from label_editor import main as gui_main

    gui_main()


def main():
    parser = build_parser()
    args = parser.parse_args()
    actions = any(
        (args.list_devices, args.image, args.status, args.config, args.battery,
         args.timeout is not None, args.beep is not None, args.selftest)
    )
    if args.gui or not actions:
        launch_gui()
        return
    if args.list_devices:
        ports = available_ports()
        if not ports:
            print("No serial devices found.")
        for device, description in ports:
            print(f"{device}: {description}")
        if not any((args.image, args.status, args.config, args.battery, args.timeout is not None, args.beep is not None, args.selftest)):
            return
    if not args.device:
        parser.error("--device is required; use --list-devices to find the printer port")

    printer = NelkoPrinter(args.device)
    try:
        if args.image:
            with Image.open(args.image) as image:
                printer.print_image(image.copy(), args.density, args.copies)
            print("Print sent")
        if args.status:
            print(printer.status())
        if args.config:
            print(printer.config())
        if args.battery:
            level, charging = printer.battery()
            print(f"Battery: {level}% ({'charging' if charging else 'not charging'})")
        if args.timeout is not None:
            printer.set_timeout(args.timeout)
            print(f"Timeout set to {args.timeout} minutes")
        if args.beep is not None:
            printer.set_beep(args.beep)
            print(f"Beep {'enabled' if args.beep else 'disabled'}")
        if args.selftest:
            printer.self_test()
            print("Self-test requested")
    except (ConnectionError, TimeoutError, ValueError, OSError) as exc:
        parser.exit(1, f"Printer error: {exc}\n")


if __name__ == "__main__":
    main()
