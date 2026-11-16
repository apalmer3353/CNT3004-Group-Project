"""Text interface for the Dre client: commands, prompts, progress."""

import getpass
import socket

from dre_client_connection import ClientError, DEFAULT_PORT

HELP_TEXT = """
Commands:
  connect <server_ip> [port]     Connect and log in (default port 5000)
  dir                            List files and folders on the server
  upload <local_path>            Upload a file
  download <filename>            Download a file into ./downloads
  delete <filename>              Delete a file on the server
  subfolder create <name>        Create a folder on the server
  subfolder delete <name>        Delete an empty folder on the server
  disconnect                     Close the connection
  help                           Show this list
  quit                           Exit
"""


def ask_yes_no(question):
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def show_progress(done, total):
    """One-line progress bar, redrawn only when the % changes."""
    percent = 100 if total == 0 else done * 100 // total
    if percent == show_progress.last and done < total:
        return
    show_progress.last = -1 if done >= total else percent
    bar = "#" * (percent // 4)
    print(f"\r  [{bar:<25}] {percent:3d}%  "
          f"{done / 1048576:,.1f}/{total / 1048576:,.1f} MB",
          end="", flush=True)
    if done >= total:
        print()


show_progress.last = -1  # Last % drawn


def format_rate(size, seconds):
    seconds = max(seconds, 1e-6)
    return f"{size / 1048576:,.2f} MB in {seconds:.2f} s " \
           f"({size / 1048576 / seconds:,.2f} MB/s)"


def run_command(client, line):
    """Run one typed command. Returns False to quit."""
    parts = line.split()
    if not parts:
        return True
    command = parts[0].lower()
    args = parts[1:]

    if command in ("quit", "exit"):
        return False

    if command == "help":
        print(HELP_TEXT)

    elif command == "connect":
        if len(args) not in (1, 2):
            raise ClientError("Use: connect <server_ip> [port]")
        host = args[0]
        try:
            port = int(args[1]) if len(args) == 2 else DEFAULT_PORT
        except ValueError:
            raise ClientError("Port must be a number")

        try:
            elapsed = client.connect(host, port)
        except (socket.timeout, TimeoutError):
            raise ClientError(f"Timed out connecting to {host}:{port}")
        except ConnectionRefusedError:
            raise ClientError(f"Connection refused - is the server running "
                              f"on {host}:{port}?")
        except socket.gaierror:
            raise ClientError(f"Unknown address: {host}")
        print(f"Connected to {host}:{port} over TLS ({elapsed * 1000:.1f} ms)")

        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        ok, message = client.login(username, password)
        print(message)
        if not ok:
            client.disconnect()

    elif command == "disconnect":
        client.disconnect()
        print("Disconnected")

    elif command == "dir":
        names = client.list_dir()
        if names:
            print(f"{len(names)} item(s) on server:")
            for name in names:
                print("  " + name)
        else:
            print("Server storage is empty")

    elif command == "upload":
        if len(args) < 1:
            raise ClientError("Use: upload <local_path>")
        path = " ".join(args).strip('"')
        result = client.upload(
            path,
            lambda name: ask_yes_no(f"'{name}' already exists on the server. Overwrite?"),
            show_progress,
        )
        if result[0]:
            print(f"Upload complete: {format_rate(result[2], result[3])}")
        else:
            print(f"Upload failed: {result[1]}")

    elif command == "download":
        if len(args) != 1:
            raise ClientError("Use: download <filename>")
        result = client.download(
            args[0],
            lambda path: ask_yes_no(f"'{path}' already exists locally. Overwrite?"),
            show_progress,
        )
        if result[0]:
            print(f"Saved to {result[1]}: {format_rate(result[2], result[3])}")
        else:
            print(f"Download failed: {result[1]}")

    elif command == "delete":
        if len(args) != 1:
            raise ClientError("Use: delete <filename>")
        ok, message = client.delete(args[0])
        print(message)

    elif command == "subfolder":
        if len(args) != 2 or args[0].lower() not in ("create", "delete"):
            raise ClientError("Use: subfolder {create|delete} <name>")
        if args[0].lower() == "create":
            ok, message = client.make_folder(args[1])
        else:
            ok, message = client.remove_folder(args[1])
        print(message)

    else:
        print(f"Unknown command '{command}'. Type 'help' for the list.")

    return True
