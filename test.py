"""Unit tests for label rendering and printer command generation."""

import tempfile
import unittest
from pathlib import Path

from label_model import LabelDocument
from printer import LABEL_HEIGHT, LABEL_WIDTH, build_print_command, crc16, image_to_bytes


class LabelDocumentTests(unittest.TestCase):
    def test_text_renders_and_round_trips(self):
        document = LabelDocument()
        element = document.add_text("Hello")
        element.x = 4
        element.y = 10

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.p21label"
            document.save(path)
            loaded = LabelDocument.load(path)

        self.assertEqual(loaded.elements[0].text, "Hello")
        self.assertEqual(loaded.render().size, (LABEL_WIDTH, LABEL_HEIGHT))
        self.assertNotEqual(loaded.render().getbbox(), None)

    def test_image_data_has_fixed_printer_size(self):
        data = image_to_bytes(LabelDocument().render())
        self.assertEqual(len(data), 3408)


class PrinterProtocolTests(unittest.TestCase):
    def test_crc_known_value(self):
        self.assertEqual(crc16(b"123456789"), bytes.fromhex("4b37"))

    def test_print_command_contains_settings_and_bitmap(self):
        command = build_print_command(b"\xff" * 3408, density=9, copies=2)
        self.assertIn(b"DENSITY 9\r\n", command)
        self.assertTrue(command.endswith(b"PRINT 2\r\n"))

    def test_invalid_print_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            build_print_command(b"", density=0, copies=1)
        with self.assertRaises(ValueError):
            build_print_command(b"", density=1, copies=0)


if __name__ == "__main__":
    unittest.main()
