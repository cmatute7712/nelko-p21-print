# Nelko P21 label printer script and capture

This repository contains a Wireshark capture of the Bluetooth traffic from a Nelko P21 label printer and a simple Python script that makes it possible to print labels without the official app.

## Requirements

- Python 3.10 or newer
- A Nelko P21 paired through Bluetooth Classic
- A serial Bluetooth connection using SPP/RFCOMM
- Windows or Linux

The script communicates directly with the serial port created for the printer's Bluetooth SPP service. On Linux it defaults to `/dev/rfcomm0`. On Windows, pass the printer's assigned COM port with `--device`.

## Installation

Clone the repository, create a virtual environment, and install the Python dependencies.

On Windows (PowerShell):

```powershell
cd nelko-p21-print
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux:

```bash
cd nelko-p21-print
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Display the available command-line options with:

```bash
python p21_print.py --help
```

## Finding available serial ports

After pairing the printer, list the serial ports visible to Python:

```bash
python p21_print.py --list-devices
```

The output includes each port name and its operating-system description. Look for a Bluetooth or Nelko-related entry. If the description is ambiguous, compare the list before and after pairing or powering on the printer.

## Connecting the printer on Windows

1. Power on the Nelko P21.
2. Open **Settings > Bluetooth & devices > Add device > Bluetooth** and pair the printer.
3. Run `python p21_print.py --list-devices` to find the outgoing Bluetooth COM port, such as `COM5`.
4. Pass that port to every command with `--device`:

```powershell
python p21_print.py --device COM5 --status
python p21_print.py --device COM5 --image test-template.png
```

Windows creates and manages the Bluetooth serial connection, so an `rfcomm connect` command is not needed. If no suitable COM port appears, open **More Bluetooth settings**, inspect the **COM Ports** tab, and add an outgoing port for the printer's serial service if necessary.

## Connecting the printer on Linux

The printer works over a Bluetooth Classic serial connection, sometimes called SPP or RFCOMM. Power on the printer and pair it using your desktop Bluetooth settings, `bluetoothctl`, or another Bluetooth tool.

Find the printer's Bluetooth MAC address, then create an RFCOMM serial connection:

```bash
sudo rfcomm connect /dev/rfcomm0 XX:XX:XX:XX:XX:XX
```

Replace `XX:XX:XX:XX:XX:XX` with the printer's Bluetooth MAC address. Keep this command running while using the printer. Open another terminal, activate the virtual environment, and run `p21_print.py` there.

If the serial device is somewhere other than `/dev/rfcomm0`, specify it with `--device`:

```bash
python p21_print.py --device /dev/rfcomm1 --status
```

Your user must have permission to access the serial device. Depending on the Linux distribution, this may require membership in the `dialout` group or running the script with appropriate permissions.

In all examples below, Windows users should add their COM port, such as `--device COM5`. Linux users need `--device` only when they are not using `/dev/rfcomm0`.

## Printing an image

Print one copy using the default density of 15:

```bash
python p21_print.py --image test-template.png
```

Print three copies at a lighter density:

```bash
python p21_print.py --image test-template.png --density 10 --copies 3
```

The current print command is designed for 14 x 40 mm labels. The script converts the image to grayscale, increases its contrast, rotates it when it is wider than tall, resizes it to fit within 96 x 284 pixels, and converts it to one-bit black and white using Floyd-Steinberg dithering.

For predictable results, prepare portrait-oriented artwork with a 96:284 aspect ratio. High-contrast images, text, and line art generally print best. The `--density` setting ranges from 1 through 15; higher values produce a darker print.

## Inspecting the printer

Show the printer's readiness and information about the loaded label:

```bash
python p21_print.py --status
```

Show the printer resolution, firmware versions, timeout, and beep configuration:

```bash
python p21_print.py --config
```

Show the battery level and charging state:

```bash
python p21_print.py --battery
```

The printer may report 99% while connected to power. Unplug it to obtain a useful battery reading.

Run the printer's built-in self-test:

```bash
python p21_print.py --selftest
```

Enable raw diagnostic information with `--debug`:

```bash
python p21_print.py --status --debug
```

Several read-only operations can be requested at once:

```bash
python p21_print.py --status --battery --config
```

## Changing printer settings

Set the automatic power-off timeout to 15, 30, or 60 minutes:

```bash
python p21_print.py --timeout 30
```

Enable the printer beep:

```bash
python p21_print.py --beep True
```

Disable the printer beep with:

```bash
python p21_print.py --beep false
```

Boolean values may be written as `true`/`false`, `yes`/`no`, `on`/`off`, or `1`/`0`.

Disable the automatic power-off timeout with:

```bash
python p21_print.py --timeout 0
```

## Command-line options

| Option | Description |
| --- | --- |
| `--device PATH` | Serial device, such as `/dev/rfcomm0` or `COM5`; required on Windows |
| `--list-devices` | List available serial ports and exit |
| `--image FILE` | Image to print |
| `--density 1-15` | Print darkness; defaults to `15` |
| `--copies NUMBER` | Number of copies; defaults to `1` |
| `--status` | Show printer and loaded-label status |
| `--config` | Show device configuration |
| `--battery` | Show battery and charging status |
| `--timeout MINUTES` | Set timeout to `0`, `15`, `30`, or `60` minutes |
| `--beep BOOLEAN` | Enable or disable the printer beep |
| `--selftest` | Run the built-in self-test print |
| `--debug` | Show additional serial and status information |

## Current limitations

- Printing is currently hard-coded for 14 x 40 mm labels and a 96 x 284-pixel bitmap.
- A failed serial connection may lead to a secondary error because some callers expect a response from the printer.
- Windows Bluetooth drivers may expose more than one COM port for a paired device. Use the outgoing port associated with the printer's serial service.

## The captured traffic and the printers protocol

It contains a connection and a print of the default template on a 14x40mm label. The entire communication of the printer runs via SPP/RFCOMM aka a serial connection over Bluetooth. The printer also has an internal NFC reader to identify the the label rolls put inside. It automatically determines the format of the labels this way. It also seems to be a type of soft DRM, where the app complains, if you use third-party label rolls.

The printer itself uses some proprietary commands like the following. Every command must be followed by a CRLF as is every response. 
- `BATTERY?`  
  Responds with: `BATTERY ` followed by two bytes. The first byte is most likely the charge level in percent.
- `CONFIG?` 
  Responds with: `CONFIG ` followed by something like `00cb0000030402040201`. 
  The first byte may indicate some protocol type, in this case TSPL2 and the second to the DPI resolution of 203 (CB).
  The next three bytes `00 00 03` corresponds to the first firmware version in the app (0.3.0).
  The three bytes after that `04 02 04` corresponds to the second firmware version in the app (4.2.4).
  Then comes one byte containing the timeout setting: `00` to `03` for never, 15 min, 30 min, 60 min.
  The last byte is the status of the beep setting.
- `BEEP` followed by a space and 0x00 or 0x01. 
- `[ESC]!o`  
  According to the TSPL2 documentation this cancels the pause status of the printer. The command is sent repeatedly from the app to the printer and the printer answers with a short status.
- `[ESC]!?`
  Seems to return the ready status for the printer.

The sent printing commands correspond to parts of TSPL2:

```plaintext
SIZE 14.0 mm,40.0 mm
GAP 5.0 mm,0 mm
DIRECTION 0,0
DENSITY 15
CLS
BITMAP 0,0,12,284,1,?????AT???GuC??
... [truncated]
```

It only supports a subset of TSPL2 commands like:

- SIZE: Sets the size of the labels.
- GAP: Sets the gap between the labels.
- DIRECTION: Controls the print direction. In case of the P21 it doesn't seem to change anything.
- DENSITY: Controls the print density/darkness of the print.
- CLS: Clears the print canvas.
- BITMAP: Prints an image and takes the parameters Xpos, YPos, height in bytes, width in dots.
- SELFTEST: This triggers the test print, the printer generates when hitting the power button once.
- PRINT x: Prints x copies of the label
- BAR: prints only a completely black label
- BARCODE: might do something, but doesn't correspond to the TSPL2 syntax. I saw it print a slightly messy black bar. I skipped all other barcode commands, after checking if QRCODE works. It doesn't.
- INITIALPRINTER: Triggers a factory reset.

The image format is 96x284 pixels in 1 bit color depth as raw data. Every bit is a pixel there are no checksums or error correction data.

The printer also exposes a serial USB connection to the PC but only returns `ERROR0` on any command.

Internally it uses a JieLi AC6951C (or similiar) bluetooth chip (see https://github.com/kagaimiq/jielie/pull/6).

Nelkos app also uses JieLis ota update feature. It checks for updates at this url: http://app.nelko.net/api/firmware/verify with a POST request:

```json
{"hardwareName":"0.0.3","dev":"P21","firmwareName":"4.2.4"}
```

There seems to be no way to get the URL for the current firmware. The app is very chatty and even sends the entire device metadata to the server. And seemingly via plain HTTP.
