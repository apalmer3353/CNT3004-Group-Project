"""Network and protocol logic for the Dre client."""

import os
import socket
import ssl
import time

# Statistics are optional
try:
    from dre_network_monitor import NetworkMonitor
except ImportError:
    NetworkMonitor = None

CHUNK_SIZE = 65536            # Matches the server
DEFAULT_PORT = 5000           # Server port
SOCKET_TIMEOUT = 60           # Seconds
CERT_FILE = "server.crt"      # Copied from the server
DOWNLOAD_DIR = "downloads"


class ClientError(Exception):
    """Error shown to the user."""


class DreClient:
    """Connection and server protocol."""

    def __init__(self, cert_file=CERT_FILE):
        self.cert_file = cert_file
        self.sock = None
        self.stream = None  # Reads lines and file data
        self.address = None
        self.monitor = None

        if NetworkMonitor is not None:
            try:
                self.monitor = NetworkMonitor()
            except Exception as error:
                print(f"[warning] Statistics disabled: {error}")

    @property
    def connected(self):
        return self.sock is not None

    def _send_line(self, text):
        self.sock.sendall((text + "\n").encode())

    def _read_line(self):
        """Read one line; raises if the server closed."""
        data = self.stream.readline()
        if not data:
            raise ConnectionError("Server closed the connection")
        return data.decode(errors="replace").rstrip("\r\n")

    def _record(self, event, filename=None, size=0, duration=0.0,
                response_ms=None, status="OK"):
        """Save one measurement for the report."""
        if self.monitor is None:
            return
        try:
            self.monitor.record(
                role="client",
                client_address=f"{self.address[0]}:{self.address[1]}"
                if self.address else None,
                event_type=event,
                filename=filename,
                bytes_transferred=size,
                duration=duration,
                response=response_ms,
                status=status,
            )
        except Exception as error:
            print(f"[warning] Could not save statistics: {error}")

    def _require_connection(self):
        if not self.connected:
            raise ClientError("Not connected. Use: connect <server_ip> <port>")

    def connect(self, host, port):
        """Open a TLS connection."""
        if self.connected:
            raise ClientError("Already connected. Use 'disconnect' first.")

        if not os.path.isfile(self.cert_file):
            raise ClientError(
                f"Missing {self.cert_file}. Copy server.crt from the server "
                "computer into this folder."
            )

        # Trust only server.crt; skip the IP check since hotspot IPs change
        context = ssl.create_default_context(cafile=self.cert_file)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED

        start = time.perf_counter()
        raw = socket.create_connection((host, port), timeout=SOCKET_TIMEOUT)
        try:
            self.sock = context.wrap_socket(raw, server_hostname=host)
        except ssl.SSLError as error:
            raw.close()
            raise ClientError(
                f"TLS failed ({error.reason}). Make sure server.crt matches "
                "the certificate the server is using."
            )
        elapsed = time.perf_counter() - start

        self.sock.settimeout(SOCKET_TIMEOUT)
        self.stream = self.sock.makefile("rb")
        self.address = (host, port)
        self._record("CONNECT", duration=elapsed, response_ms=elapsed * 1000)
        return elapsed

    def login(self, username, password):
        """Log in (password is sent encrypted by TLS)."""
        self._require_connection()
        start = time.perf_counter()

        prompt = self._read_line()
        if prompt != "Username:":
            raise ClientError(f"Unexpected server message: {prompt}")
        self._send_line(username)

        prompt = self._read_line()
        if prompt != "Password:":
            raise ClientError(f"Unexpected server message: {prompt}")
        self._send_line(password)

        result = self._read_line()
        elapsed = time.perf_counter() - start
        ok = result == "Login successful"
        self._record("LOGIN", duration=elapsed, response_ms=elapsed * 1000,
                     status="OK" if ok else "FAILED")
        return ok, result

    def disconnect(self):
        for item in (self.stream, self.sock):
            try:
                if item is not None:
                    item.close()
            except OSError:
                pass
        self.sock = None
        self.stream = None
        self.address = None

    def _simple_command(self, event, command, name=None):
        """Send a command, return the reply."""
        self._require_connection()
        start = time.perf_counter()
        self._send_line(command)
        reply = self._read_line()
        elapsed = time.perf_counter() - start
        ok = "successfully" in reply
        self._record(event, filename=name, duration=elapsed,
                     response_ms=elapsed * 1000,
                     status="OK" if ok else "ERROR")
        return ok, reply

    def list_dir(self):
        """Reply is 'DIR <count>' then one name per line."""
        self._require_connection()
        start = time.perf_counter()
        self._send_line("DIR")
        header = self._read_line()
        parts = header.split()
        if len(parts) != 2 or parts[0] != "DIR" or not parts[1].isdigit():
            raise ClientError(f"Unexpected server message: {header}")
        names = [self._read_line() for _ in range(int(parts[1]))]
        elapsed = time.perf_counter() - start
        self._record("DIR", duration=elapsed, response_ms=elapsed * 1000)
        return names

    def delete(self, filename):
        return self._simple_command("DELETE", f"DELETE {filename}", filename)

    def make_folder(self, name):
        return self._simple_command("MKDIR", f"MKDIR {name}", name)

    def remove_folder(self, name):
        return self._simple_command("RMDIR", f"RMDIR {name}", name)

    def upload(self, local_path, confirm_overwrite, progress=None):
        """Upload a file; asks confirm_overwrite() if it exists."""
        self._require_connection()

        if not os.path.isfile(local_path):
            raise ClientError(f"Local file not found: {local_path}")

        filename = os.path.basename(local_path)
        if " " in filename:
            raise ClientError(
                "The server does not accept spaces in filenames. "
                "Rename the file first (e.g. use underscores)."
            )
        size = os.path.getsize(local_path)

        start = time.perf_counter()
        self._send_line(f"UPLOAD {filename} {size}")
        reply = self._read_line()
        response_ms = (time.perf_counter() - start) * 1000

        if reply == "OVERWRITE?":
            answer = confirm_overwrite(filename)
            self._send_line("YES" if answer else "NO")
            reply = self._read_line()

        if reply != "READY":
            self._record("UPLOAD", filename, 0, time.perf_counter() - start,
                         response_ms, "ERROR")
            return False, reply

        transfer_start = time.perf_counter()
        sent = 0
        with open(local_path, "rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                self.sock.sendall(chunk)
                sent += len(chunk)
                if progress:
                    progress(sent, size)

        reply = self._read_line()
        duration = time.perf_counter() - transfer_start
        ok = reply == "Upload complete"
        self._record("UPLOAD", filename, sent, duration, response_ms,
                     "OK" if ok else "ERROR")
        return ok, reply, sent, duration

    def download(self, filename, confirm_local_overwrite, progress=None):
        """Download into ./downloads. Reply is 'SIZE <n>' then the bytes."""
        self._require_connection()
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        local_path = os.path.join(DOWNLOAD_DIR, os.path.basename(filename))

        if os.path.exists(local_path) and not confirm_local_overwrite(local_path):
            return False, "Download cancelled"

        start = time.perf_counter()
        self._send_line(f"DOWNLOAD {filename}")
        reply = self._read_line()
        response_ms = (time.perf_counter() - start) * 1000

        parts = reply.split()
        if len(parts) != 2 or parts[0] != "SIZE" or not parts[1].isdigit():
            self._record("DOWNLOAD", filename, 0, time.perf_counter() - start,
                         response_ms, "ERROR")
            return False, reply

        size = int(parts[1])
        temp_path = local_path + ".part"
        transfer_start = time.perf_counter()
        received = 0
        try:
            with open(temp_path, "wb") as output:
                while received < size:
                    chunk = self.stream.read(min(CHUNK_SIZE, size - received))
                    if not chunk:
                        raise ConnectionError("Download interrupted")
                    output.write(chunk)
                    received += len(chunk)
                    if progress:
                        progress(received, size)
            os.replace(temp_path, local_path)
        except (OSError, ConnectionError):
            self._record("DOWNLOAD", filename, received,
                         time.perf_counter() - transfer_start,
                         response_ms, "INTERRUPTED")
            raise

        duration = time.perf_counter() - transfer_start
        self._record("DOWNLOAD", filename, received, duration, response_ms)
        return True, local_path, received, duration
