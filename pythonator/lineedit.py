import os
import pathlib
import select
import shutil
import sys
import tempfile
import termios

ANSI = "\033["
RESET = "\033[0m"
DIM = "\033[2m"

def strip_ansi(text):
    out = []
    index = 0
    while index < len(text):
        if text[index] == "\033" and index + 1 < len(text) and text[index + 1] == "[":
            index += 2
            while index < len(text) and not ("@" <= text[index] <= "~"):
                index += 1
            index += 1
            continue
        out.append(text[index])
        index += 1
    return "".join(out)

def term_width():
    return shutil.get_terminal_size((80, 24)).columns

class LineEditor:
    def __init__(self, history_path):
        self.history_path = pathlib.Path(history_path)
        self.history = self.load_history()
        self.is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        self.fd = sys.stdin.fileno() if self.is_tty else None
        self.original = None
        self.transient = False
        self.transient_prompt = ""
        self.right_status = ""
        self.was_transient = False

    def load_history(self):
        try:
            lines = self.history_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            cleaned = []
            for line in lines:
                line = "".join(ch for ch in line if ch.isprintable())
                if line:
                    cleaned.append(line)
            return cleaned[-200:]
        except OSError:
            return []

    def save_history(self):
        tmp = None
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix="pythonator_history_", dir=str(self.history_path.parent))
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                for line in self.history[-200:]:
                    handle.write(line + "\n")
            os.replace(tmp, self.history_path)
        except OSError:
            pass
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)

    def add_history(self, line):
        if not line:
            return
        if self.history and self.history[-1] == line:
            return
        self.history.append(line)
        self.history = self.history[-200:]
        self.save_history()

    def enter_raw(self):
        if not self.is_tty:
            return
        self.original = termios.tcgetattr(self.fd)
        raw = termios.tcgetattr(self.fd)
        raw[3] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
        raw[0] &= ~(termios.ICRNL | termios.INLCR | termios.IGNCR | termios.IXON | termios.IXOFF)
        raw[6][termios.VMIN] = 1
        raw[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, raw)
        sys.stdout.write(ANSI + "?2004h")
        sys.stdout.flush()

    def leave_raw(self):
        if not self.is_tty or self.original is None:
            return
        sys.stdout.write(ANSI + "?2004l")
        sys.stdout.flush()
        termios.tcsetattr(self.fd, termios.TCSANOW, self.original)
        self.original = None

    def ghost_suffix(self, buffer):
        for entry in reversed(self.history):
            if entry.startswith(buffer) and len(entry) > len(buffer):
                return entry[len(buffer):]
        return ""

    def redraw(self, prompt, buffer, cursor):
        out = ["\r"]
        use_transient = self.transient and bool(self.transient_prompt)
        if use_transient:
            self.was_transient = True
            out.extend([ANSI + "K", ANSI + "1A", ANSI + "K", DIM, "─" * term_width(), RESET, ANSI + "1B", "\r", ANSI + "K"])
        else:
            if self.was_transient:
                out.extend([ANSI + "1A", ANSI + "K", ANSI + "1B"])
                self.was_transient = False
            out.append(ANSI + "K")
        shown_prompt = self.transient_prompt if use_transient else prompt
        out.append(shown_prompt)
        out.append(buffer)
        ghost_len = 0
        if cursor == len(buffer) and buffer:
            suffix = self.ghost_suffix(buffer)
            if suffix:
                out.extend([DIM, suffix, RESET])
                ghost_len = len(suffix)
        if ghost_len:
            out.append(ANSI + f"{ghost_len}D")
        if self.right_status:
            status = strip_ansi(self.right_status)
            column = max(0, term_width() - len(status))
            out.extend([ANSI + "s", ANSI + f"{column + 1}G", DIM, status, RESET, ANSI + "u"])
        left = len(buffer) - cursor
        if left > 0:
            out.append(ANSI + f"{left}D")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def read_key(self):
        first = os.read(self.fd, 1)
        if not first:
            return ("eof", "")
        value = first[0]
        if value != 0x1B:
            if value == 0x03: return ("ctrl_c", "")
            if value == 0x04: return ("ctrl_d", "")
            if value in (0x0A, 0x0D): return ("enter", "")
            if value == 0x7F: return ("backspace", "")
            if value == 0x01: return ("ctrl_a", "")
            if value == 0x05: return ("ctrl_e", "")
            if value == 0x15: return ("ctrl_u", "")
            if value == 0x0B: return ("ctrl_k", "")
            if value == 0x0C: return ("ctrl_l", "")
            if value == 0x06: return ("ctrl_f", "")
            if value == 0x09 or value < 0x20: return ("ignore", "")
            if value >= 0x80:
                extra = 1 if value < 0xE0 else (2 if value < 0xF0 else 3)
                buf = bytearray([value])
                for _ in range(extra):
                    b = os.read(self.fd, 1)
                    if not b:
                        break
                    buf += b
                try:
                    return ("char", buf.decode("utf-8"))
                except UnicodeDecodeError:
                    return ("ignore", "")
            return ("char", chr(value))
        ready, _, _ = select.select([self.fd], [], [], 0.12)
        if not ready:
            return ("ignore", "")
        second = os.read(self.fd, 1)
        if not second or second != b"[":
            return ("ignore", "")
        params = ""
        while True:
            byte = os.read(self.fd, 1)
            if not byte:
                return ("ignore", "")
            code = byte[0]
            if 0x40 <= code <= 0x7E:
                if code == 0x41: return ("up", "")
                if code == 0x42: return ("down", "")
                if code == 0x43: return ("right", "")
                if code == 0x44: return ("left", "")
                if code == 0x48: return ("home", "")
                if code == 0x46: return ("end", "")
                if code == 0x7E:
                    if params in ("1", "7"): return ("home", "")
                    if params in ("4", "8"): return ("end", "")
                    if params == "3": return ("delete", "")
                    if params == "200":
                        data = bytearray()
                        while True:
                            byte = os.read(self.fd, 1)
                            if not byte:
                                break
                            if byte == b"\x1b":
                                ready, _, _ = select.select([self.fd], [], [], 0.05)
                                if ready and os.read(self.fd, 1) == b"[":
                                    seq = bytearray()
                                    while True:
                                        code = os.read(self.fd, 1)
                                        if not code:
                                            break
                                        if b"@" <= code <= b"~":
                                            if code == b"~" and bytes(seq) == b"201":
                                                return ("paste", data.decode("utf-8", "ignore"))
                                            break
                                        seq.extend(code)
                                    continue
                                data.extend(b"\x1b")
                                continue
                            data.extend(byte)
                        return ("paste", data.decode("utf-8", "ignore"))
                return ("ignore", "")
            params += chr(code)

    def history_up(self, buffer, cursor, nav):
        if nav["index"] == -1:
            nav["prefix"] = buffer
            nav["index"] = len(self.history)
        for index in range(nav["index"] - 1, -1, -1):
            if self.history[index].startswith(nav["prefix"]):
                nav["index"] = index
                return self.history[index], len(self.history[index])
        return buffer, cursor

    def history_down(self, buffer, cursor, nav):
        if nav["index"] == -1:
            return buffer, cursor
        for index in range(nav["index"] + 1, len(self.history)):
            if self.history[index].startswith(nav["prefix"]):
                nav["index"] = index
                return self.history[index], len(self.history[index])
        nav["index"] = -1
        return nav["prefix"], len(nav["prefix"])

    def edit(self, prompt):
        if not self.is_tty:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.rstrip("\n").rstrip("\r")
            self.add_history(line)
            return line
        self.enter_raw()
        buffer = ""
        cursor = 0
        nav = {"index": -1, "prefix": ""}
        self.transient = False
        self.was_transient = False
        self.redraw(prompt, buffer, cursor)
        submitted = False
        try:
            while True:
                key, data = self.read_key()
                if key == "eof":
                    break
                if key == "ignore":
                    continue
                if key == "enter":
                    submitted = True
                    break
                if key == "ctrl_c":
                    buffer = ""
                    cursor = 0
                    nav["index"] = -1
                    self.transient = True
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "ctrl_d":
                    if not buffer:
                        break
                    if cursor < len(buffer):
                        buffer = buffer[:cursor] + buffer[cursor + 1:]
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "ctrl_u":
                    buffer = buffer[cursor:]
                    cursor = 0
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "ctrl_k":
                    buffer = buffer[:cursor]
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "ctrl_a":
                    cursor = 0
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "ctrl_e":
                    cursor = len(buffer)
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "ctrl_l":
                    self.transient = False
                    sys.stdout.write(ANSI + "2J" + ANSI + "H")
                    sys.stdout.flush()
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "ctrl_f":
                    if cursor == len(buffer) and buffer:
                        buffer += self.ghost_suffix(buffer)
                        cursor = len(buffer)
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "up":
                    buffer, cursor = self.history_up(buffer, cursor, nav)
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "down":
                    buffer, cursor = self.history_down(buffer, cursor, nav)
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "left":
                    cursor = max(0, cursor - 1)
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "right":
                    if cursor == len(buffer) and buffer:
                        suffix = self.ghost_suffix(buffer)
                        if suffix:
                            buffer += suffix
                            cursor = len(buffer)
                            self.redraw(prompt, buffer, cursor)
                            continue
                    cursor = min(len(buffer), cursor + 1)
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "home":
                    cursor = 0
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "end":
                    cursor = len(buffer)
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "delete":
                    if cursor < len(buffer):
                        buffer = buffer[:cursor] + buffer[cursor + 1:]
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "backspace":
                    if cursor > 0:
                        buffer = buffer[:cursor - 1] + buffer[cursor:]
                        cursor -= 1
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "paste":
                    self.transient = False
                    buffer = buffer[:cursor] + data + buffer[cursor:]
                    cursor += len(data)
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
                    continue
                if key == "char":
                    self.transient = False
                    buffer = buffer[:cursor] + data + buffer[cursor:]
                    cursor += len(data)
                    nav["index"] = -1
                    self.redraw(prompt, buffer, cursor)
        finally:
            self.leave_raw()
        if submitted:
            self.add_history(buffer)
            return buffer
        return None
