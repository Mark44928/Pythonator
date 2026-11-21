import os
import tempfile
import unittest

from pythonator.lineedit import LineEditor


class ReadKeyTests(unittest.TestCase):
    def editor_with(self, data: bytes) -> tuple[LineEditor, int]:
        read_fd, write_fd = os.pipe()
        os.write(write_fd, data)
        os.close(write_fd)
        editor = LineEditor(os.path.join(tempfile.gettempdir(), "pythonator_history_test"))
        editor.fd = read_fd
        return editor, read_fd

    def test_multibyte_utf8_round_trips(self):
        editor, fd = self.editor_with("é".encode())
        try:
            self.assertEqual(editor.read_key(), ("char", "é"))
        finally:
            os.close(fd)

    def test_four_byte_utf8_round_trips(self):
        editor, fd = self.editor_with("😀".encode())
        try:
            self.assertEqual(editor.read_key(), ("char", "😀"))
        finally:
            os.close(fd)

    def test_ascii_still_reads(self):
        editor, fd = self.editor_with(b"a")
        try:
            self.assertEqual(editor.read_key(), ("char", "a"))
        finally:
            os.close(fd)


if __name__ == "__main__":
    unittest.main()
