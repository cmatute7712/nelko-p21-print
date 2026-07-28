# Nelko P21 Label Studio

This repository contains a cross-platform graphical label editor for the Nelko P21 printer, a command-line interface, and the original Wireshark protocol capture. It can compose text and images, save reusable label projects, export print-ready PNG files, and print without the official app.

## Features

- Visual 14 x 40 mm label canvas with a live monochrome preview
- Text elements with editable content, size, and position
- PNG, JPEG, BMP, and GIF image elements with editable size and position
- Drag-to-position editing
- Save and reopen `.p21label` project files
- Export labels as 96 x 284-pixel PNG images
- Windows COM port and Linux RFCOMM support
- Printer status, battery, timeout, beep, density, copy count, and self-test controls
- Command-line printing and administration for automation

## Choose an interface

| Interface | Best for | Platforms | Start command |
| --- | --- | --- | --- |
| Desktop GUI | Direct use on a workstation with local Bluetooth | Windows and Linux | `.\run.ps1` or `./run.sh` |
| Docker web app | Browser access on a Linux machine hosting the printer | Linux Docker host | `docker compose up --build` |
| Command line | Automation and diagnostics | Windows and Linux | `.\run.ps1 --help` or `./run.sh --help` |

Both graphical editors use the same 96 x 284-pixel, 14 x 40 mm print area and expose the same core printer controls. The desktop and web project formats both use the `.p21label` extension, but image handling differs: desktop projects reference local image paths, while web projects embed their images.

# Desktop Python application

## Desktop requirements

- Python 3.9 or newer
- A Nelko P21 paired through Bluetooth Classic
- A serial Bluetooth connection using SPP/RFCOMM
- Windows or Linux

Tkinter is included with the standard Python installer on Windows. Some Linux distributions package it separately; for example, Debian and Ubuntu users can install it with `sudo apt install python3-tk`.

The script communicates directly with the serial port created for the printer's Bluetooth SPP service. On Linux it defaults to `/dev/rfcomm0`. On Windows, pass the printer's assigned COM port with `--device`.

## Desktop installation and launch

The included launch scripts create a `.venv` virtual environment when it is missing, install the project requirements, and start the application. Run them again whenever you want to open the editor.

On Windows (PowerShell):

```powershell
.\run.ps1
```

On Linux or macOS:

```bash
chmod +x run.sh
./run.sh
```

Arguments are passed through to `p21_print.py`. For example, display the command-line help with:

```powershell
.\run.ps1 --help
```

The launcher opens the desktop GUI when no arguments are supplied. You can also start it directly from an activated environment:

```bash
python p21_print.py --gui
```

On Windows, you can use `py p21_print.py` in place of `python p21_print.py`.

## Using the desktop editor

1. Select **Add text** or **Add image** from the toolbar.
2. Click an element in the preview to select it.
3. Drag the selected element to reposition it, or enter exact X and Y coordinates in the properties panel.
4. Edit text and font size, or set the maximum width and height of an image, then select **Apply changes**.
5. Use **File > Save As** to save an editable `.p21label` project.
6. Use **Export PNG** to create a 96 x 284-pixel rendered label without printing it.

Coordinates and dimensions are measured in printer pixels. The P21 print area is 96 pixels wide by 284 pixels tall. Content outside the label bounds is clipped.

Desktop project files contain text and layout settings plus absolute paths to imported images. Keep the source image files at those paths when reopening a desktop project.

## Printing from the editor

1. Pair and connect the printer using the Windows or Linux instructions below.
2. Choose its serial port in the **Printer** panel. Select **Refresh** to rescan available ports.
3. Set print density from 1 (lightest) to 15 (darkest) and choose the number of copies.
4. Select **Status** to verify the connection, then select **Print**.

Printer communication runs in a background thread so the editor remains responsive while waiting for the device. Connection and protocol errors are shown in an error dialog.

Select **Settings...** to read printer configuration or battery status, change the power-off timeout and beep setting, or request a self-test print.

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

## Printing an image from the command line

Print one copy using the default density of 15:

```bash
python p21_print.py --image test-template.png
```

Print three copies at a lighter density:

```bash
python p21_print.py --image test-template.png --density 10 --copies 3
```

The current print command is designed for 14 x 40 mm labels. It resizes the supplied image to 96 x 284 pixels and converts it to one-bit black and white using Floyd-Steinberg dithering. Use the GUI or export a correctly sized PNG first when preserving the source image's aspect ratio is important.

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
| `--gui` | Open the graphical label editor |
| `--device PATH` | Serial device, such as `/dev/rfcomm0` or `COM5`; required for Windows CLI printer commands |
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

## Desktop and CLI limitations

- Printing is currently hard-coded for 14 x 40 mm labels and a 96 x 284-pixel bitmap.
- Windows Bluetooth drivers may expose more than one COM port for a paired device. Use the outgoing port associated with the printer's serial service.
- `.p21label` files reference imported images by absolute path rather than embedding them.

# Docker web application

The browser version provides draggable text and image elements, portable project files with embedded images, PNG export, printer discovery, printing, and printer settings from a responsive interface. It uses the Flask API in `web_app.py`, serves through Gunicorn, and includes a container health check.

The container integration targets a **Linux Docker host**. Docker Desktop on Windows does not pass host Bluetooth COM ports into Linux containers; use the native Windows desktop application in that environment.

## Web application requirements

- A Linux host with Docker Engine and Docker Compose
- A paired Nelko P21
- BlueZ and the `rfcomm` command on the host
- `/dev/rfcomm0` created before the container starts

The Compose setup deliberately does not run as a privileged container. It maps only `/dev/rfcomm0` and publishes the web interface only on `127.0.0.1`.

## Connect Bluetooth for Docker

Pair the printer on the Linux host, then create `/dev/rfcomm0` before starting Compose:

```bash
sudo rfcomm bind /dev/rfcomm0 XX:XX:XX:XX:XX:XX 1
ls -l /dev/rfcomm0
```

Replace the placeholder with the printer's Bluetooth MAC address. The host remains responsible for Bluetooth pairing and RFCOMM management. The container receives only `/dev/rfcomm0`; it is not privileged and does not receive all host devices or the system D-Bus socket.

If the printer uses another RFCOMM device, change both sides of the device mapping in `compose.yml` and enter that path in the web interface.

## Start the web server

```bash
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) in a browser. Compose binds the site to localhost by default because the printer API has no authentication. Do not expose it to an untrusted network. To stop it, press Ctrl+C and run:

```bash
docker compose down
```

The container includes a health check at `/health`. Label projects and imported image content remain in the browser and are downloaded as files; the container does not require a persistent data volume.

## Using the web editor

1. Open `http://localhost:8080`.
2. Use **Add text** or **Add image** to place content on the label.
3. Select and drag elements on the canvas, or enter exact values in the element panel.
4. Select a detected serial port or enter `/dev/rfcomm0`.
5. Use **Check status** to confirm communication.
6. Select print density and copy count, then select **Print label**.

Use **Save project** to download a `.p21label` file. Unlike desktop projects, web projects embed imported images as data URLs, so the downloaded file is portable. **Open** restores one of these projects, and **Export PNG** downloads the rendered 96 x 284-pixel label.

The device panel can read status, configuration, and battery information; set timeout and beep behavior; and request a self-test print. These actions call local API endpoints and require a valid mapped serial device.

## Docker configuration

The supplied `compose.yml`:

- builds the application from `Dockerfile`;
- maps host `/dev/rfcomm0` to the same path in the container;
- publishes the application at `127.0.0.1:8080`;
- restarts the service unless it was explicitly stopped.

To use a different device or port, edit `compose.yml`. If remote browser access is required, use a trusted reverse proxy with authentication and TLS instead of publishing the unauthenticated printer API directly.

## Troubleshooting

- **`run.ps1` is blocked:** allow locally created scripts for the current PowerShell session or run it from a PowerShell configuration that permits local scripts.
- **No COM port on Windows:** inspect **More Bluetooth settings > COM Ports** and use the outgoing Bluetooth serial port.
- **No `/dev/rfcomm0` on Linux:** pair the printer and create the RFCOMM binding before starting the desktop app or Compose.
- **Compose reports that `/dev/rfcomm0` is missing:** the device mapping is evaluated when the container is created. Create the host device first, then rerun `docker compose up`.
- **Permission denied opening the printer:** verify host device permissions. For the native Linux app, the user may need membership in `dialout`.
- **Docker web UI opens but printing fails:** check `docker compose logs p21-web`, confirm `/dev/rfcomm0` exists inside the container, and verify the printer is powered on and not connected exclusively to another application.

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
