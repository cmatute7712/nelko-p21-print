#!/usr/bin/env python3
"""Tkinter label editor for the Nelko P21 printer."""

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import ImageTk

from label_model import LabelDocument
from printer import DEFAULT_DEVICE, LABEL_HEIGHT, LABEL_WIDTH, NelkoPrinter, available_ports


PREVIEW_SCALE = 2


class LabelEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nelko P21 Label Editor")
        self.minsize(760, 680)
        self.document = LabelDocument()
        self.current_file = None
        self.selected = None
        self.preview_image = None
        self.drag_origin = None

        self.device_var = tk.StringVar(value=DEFAULT_DEVICE or "")
        self.density_var = tk.IntVar(value=15)
        self.copies_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Ready")
        self.text_var = tk.StringVar()
        self.font_size_var = tk.IntVar(value=18)
        self.x_var = tk.IntVar(value=0)
        self.y_var = tk.IntVar(value=0)
        self.width_var = tk.IntVar(value=72)
        self.height_var = tk.IntVar(value=72)

        self._build_menu()
        self._build_ui()
        self.refresh_ports()
        self.refresh_preview()

    def _build_menu(self):
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New", command=self.new_label, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_label, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_label, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_label_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export PNG...", command=self.export_png)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu)
        self.bind_all("<Control-n>", lambda _event: self.new_label())
        self.bind_all("<Control-o>", lambda _event: self.open_label())
        self.bind_all("<Control-s>", lambda _event: self.save_label())
        self.bind_all("<Delete>", lambda _event: self.delete_selected())

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Add text", command=self.add_text).pack(side="left")
        ttk.Button(toolbar, text="Add image", command=self.add_image).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Delete", command=self.delete_selected).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(toolbar, text="Export PNG", command=self.export_png).pack(side="left")
        ttk.Button(toolbar, text="Print", command=self.print_label).pack(side="right")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8)

        preview_frame = ttk.LabelFrame(body, text="Label preview (14 x 40 mm)", padding=12)
        body.add(preview_frame, weight=3)
        self.canvas = tk.Canvas(
            preview_frame, width=LABEL_WIDTH * PREVIEW_SCALE,
            height=LABEL_HEIGHT * PREVIEW_SCALE, background="#dddddd",
            highlightthickness=1, highlightbackground="#888888", cursor="crosshair"
        )
        self.canvas.pack(expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda _event: self._sync_properties())

        properties = ttk.LabelFrame(body, text="Selected element", padding=10)
        body.add(properties, weight=2)
        self.property_widgets = []
        self._field(properties, "Text", self.text_var)
        self._field(properties, "Font size", self.font_size_var)
        self._field(properties, "X", self.x_var)
        self._field(properties, "Y", self.y_var)
        self._field(properties, "Width", self.width_var)
        self._field(properties, "Height", self.height_var)
        ttk.Button(properties, text="Apply changes", command=self.apply_properties).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )
        ttk.Label(
            properties,
            text="Drag an element in the preview to move it. Text uses pixel-sized fonts. "
                 "Image width and height are maximum bounds.",
            wraplength=210,
        ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=12)

        printer = ttk.LabelFrame(self, text="Printer", padding=8)
        printer.pack(fill="x", padx=8, pady=8)
        ttk.Label(printer, text="Serial port").grid(row=0, column=0, sticky="w")
        self.port_box = ttk.Combobox(printer, textvariable=self.device_var, width=28)
        self.port_box.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(printer, text="Refresh", command=self.refresh_ports).grid(row=0, column=2)
        ttk.Button(printer, text="Status", command=self.show_printer_status).grid(row=0, column=3, padx=5)
        ttk.Button(printer, text="Settings...", command=self.open_printer_settings).grid(row=0, column=4)
        ttk.Label(printer, text="Density").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(printer, from_=1, to=15, textvariable=self.density_var, width=5).grid(
            row=1, column=1, sticky="w", padx=5, pady=(8, 0)
        )
        ttk.Label(printer, text="Copies").grid(row=1, column=2, sticky="e", pady=(8, 0))
        ttk.Spinbox(printer, from_=1, to=99, textvariable=self.copies_var, width=5).grid(
            row=1, column=3, sticky="w", padx=5, pady=(8, 0)
        )
        printer.columnconfigure(1, weight=1)

        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x")

    def _field(self, parent, label, variable):
        row = len(self.property_widgets)
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        entry = ttk.Entry(parent, textvariable=variable, width=20)
        entry.grid(row=row, column=1, sticky="ew", padx=(6, 0), pady=3)
        self.property_widgets.append(entry)
        parent.columnconfigure(1, weight=1)

    def refresh_preview(self):
        rendered = self.document.render().resize(
            (LABEL_WIDTH * PREVIEW_SCALE, LABEL_HEIGHT * PREVIEW_SCALE)
        )
        self.preview_image = ImageTk.PhotoImage(rendered)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_image, anchor="nw")
        if self.selected in self.document.elements:
            element = self.selected
            if element.kind == "image":
                width, height = element.width, element.height
            else:
                width = max(12, len(max(element.text.splitlines() or [""], key=len)) * element.font_size // 2)
                height = max(element.font_size, len(element.text.splitlines()) * (element.font_size + 2))
            self.canvas.create_rectangle(
                element.x * PREVIEW_SCALE, element.y * PREVIEW_SCALE,
                (element.x + width) * PREVIEW_SCALE, (element.y + height) * PREVIEW_SCALE,
                outline="#1976d2", width=2, dash=(4, 2)
            )

    def add_text(self):
        text = simpledialog.askstring("Add text", "Text:", parent=self)
        if text is not None:
            self.selected = self.document.add_text(text or "Text")
            self._sync_properties()
            self.refresh_preview()

    def add_image(self):
        path = filedialog.askopenfilename(
            title="Add image", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        if path:
            try:
                self.selected = self.document.add_image(path)
                self._sync_properties()
                self.refresh_preview()
            except Exception as exc:
                messagebox.showerror("Could not add image", str(exc), parent=self)

    def delete_selected(self):
        if self.selected in self.document.elements:
            self.document.elements.remove(self.selected)
            self.selected = None
            self.refresh_preview()

    def _sync_properties(self):
        if not self.selected:
            return
        self.text_var.set(self.selected.text if self.selected.kind == "text" else "")
        self.font_size_var.set(self.selected.font_size)
        self.x_var.set(self.selected.x)
        self.y_var.set(self.selected.y)
        self.width_var.set(self.selected.width)
        self.height_var.set(self.selected.height)

    def apply_properties(self):
        if not self.selected:
            return
        try:
            self.selected.x = max(0, min(LABEL_WIDTH - 1, self.x_var.get()))
            self.selected.y = max(0, min(LABEL_HEIGHT - 1, self.y_var.get()))
            self.selected.font_size = max(6, min(96, self.font_size_var.get()))
            self.selected.width = max(1, min(LABEL_WIDTH, self.width_var.get()))
            self.selected.height = max(1, min(LABEL_HEIGHT, self.height_var.get()))
            if self.selected.kind == "text":
                self.selected.text = self.text_var.get()
            self._sync_properties()
            self.refresh_preview()
        except tk.TclError:
            messagebox.showerror("Invalid value", "Enter whole numbers for size and position.")

    def on_canvas_press(self, event):
        x, y = event.x // PREVIEW_SCALE, event.y // PREVIEW_SCALE
        self.selected = self._element_at(x, y)
        self.drag_origin = (x, y, self.selected.x, self.selected.y) if self.selected else None
        self._sync_properties()
        self.refresh_preview()

    def _element_at(self, x, y):
        for element in reversed(self.document.elements):
            width = element.width if element.kind == "image" else max(12, len(element.text) * element.font_size // 2)
            height = element.height if element.kind == "image" else max(12, element.font_size + 4)
            if element.x <= x <= element.x + width and element.y <= y <= element.y + height:
                return element
        return None

    def on_canvas_drag(self, event):
        if not self.drag_origin or not self.selected:
            return
        start_x, start_y, element_x, element_y = self.drag_origin
        self.selected.x = max(0, min(LABEL_WIDTH - 1, element_x + event.x // PREVIEW_SCALE - start_x))
        self.selected.y = max(0, min(LABEL_HEIGHT - 1, element_y + event.y // PREVIEW_SCALE - start_y))
        self.refresh_preview()

    def new_label(self):
        self.document = LabelDocument()
        self.current_file = None
        self.selected = None
        self.title("Nelko P21 Label Editor")
        self.refresh_preview()

    def open_label(self):
        path = filedialog.askopenfilename(filetypes=[("Nelko label", "*.p21label"), ("JSON", "*.json")])
        if path:
            try:
                self.document = LabelDocument.load(path)
                self.current_file = path
                self.selected = None
                self.title(f"{Path(path).name} - Nelko P21 Label Editor")
                self.refresh_preview()
            except Exception as exc:
                messagebox.showerror("Could not open label", str(exc), parent=self)

    def save_label(self):
        if not self.current_file:
            return self.save_label_as()
        try:
            self.document.save(self.current_file)
            self.status_var.set(f"Saved {self.current_file}")
        except Exception as exc:
            messagebox.showerror("Could not save label", str(exc), parent=self)

    def save_label_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".p21label", filetypes=[("Nelko label", "*.p21label")]
        )
        if path:
            self.current_file = path
            self.save_label()
            self.title(f"{Path(path).name} - Nelko P21 Label Editor")

    def export_png(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if path:
            self.document.render().save(path)
            self.status_var.set(f"Exported {path}")

    def refresh_ports(self):
        ports = available_ports()
        self.port_box["values"] = [device for device, _description in ports]
        if not self.device_var.get() and ports:
            self.device_var.set(ports[0][0])
        descriptions = ", ".join(f"{device} ({description})" for device, description in ports)
        self.status_var.set(descriptions or "No serial ports found")

    def _printer(self):
        return NelkoPrinter(self.device_var.get().strip())

    def _background(self, label, operation, success=None):
        self.status_var.set(label)

        def run():
            try:
                result = operation()
            except Exception as exc:
                self.after(
                    0,
                    lambda error=exc: messagebox.showerror(
                        "Printer error", str(error), parent=self
                    ),
                )
                self.after(0, lambda: self.status_var.set("Printer operation failed"))
            else:
                self.after(0, lambda: self.status_var.set(success or str(result)))

        threading.Thread(target=run, daemon=True).start()

    def show_printer_status(self):
        self._background("Reading printer status...", lambda: self._printer().status())

    def print_label(self):
        try:
            density, copies = self.density_var.get(), self.copies_var.get()
            image = self.document.render()
        except tk.TclError:
            messagebox.showerror("Invalid print settings", "Density and copies must be whole numbers.")
            return
        self._background(
            "Printing...", lambda: self._printer().print_image(image, density, copies), "Print sent"
        )

    def open_printer_settings(self):
        window = tk.Toplevel(self)
        window.title("Printer settings")
        window.transient(self)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        timeout_var = tk.IntVar(value=15)
        beep_var = tk.BooleanVar(value=True)
        ttk.Label(frame, text="Power-off timeout").grid(row=0, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=timeout_var, values=(0, 15, 30, 60), width=8, state="readonly").grid(row=0, column=1, padx=8)
        ttk.Checkbutton(frame, text="Beep enabled", variable=beep_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=8)
        ttk.Button(frame, text="Read configuration", command=lambda: self._background("Reading configuration...", lambda: self._printer().config())).grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Button(frame, text="Read battery", command=lambda: self._background("Reading battery...", lambda: self._battery_text())).grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(frame, text="Apply timeout and beep", command=lambda: self._apply_settings(timeout_var.get(), beep_var.get())).grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(frame, text="Self-test print", command=lambda: self._background("Running self-test...", lambda: self._printer().self_test(), "Self-test requested")).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(5, 0))

    def _battery_text(self):
        level, charging = self._printer().battery()
        return f"Battery: {level}% ({'charging' if charging else 'not charging'})"

    def _apply_settings(self, timeout, beep):
        def apply():
            printer = self._printer()
            printer.set_timeout(timeout)
            printer.set_beep(beep)
        self._background("Applying printer settings...", apply, "Printer settings applied")


def main():
    app = LabelEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
