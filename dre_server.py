
import socket
import threading
import os

STORAGE = "server_storage"
os.makedirs(STORAGE, exist_ok=True)


def valid_filename(filename):
    return (
        filename not in ("", ".", "..")
        and os.path.basename(filename) == filename
        and "/" not in filename
        and "\\" not in filename
    )


def handle_client(client, address):
    print("Connected to:", address)
    file_stream = client.makefile("rb")

    try:
        while True:
            data = file_stream.readline()

            if not data:
                break

            message = data.decode().strip()
            print("Command:", message)

            if message.upper() == "DIR":
                files = os.listdir(STORAGE)
                response = "\n".join(files) if files else "Folder is empty"

            elif message.upper().startswith("UPLOAD "):
                parts = message.split()

                if len(parts) != 3:
                    client.sendall(b"Use: UPLOAD filename size\n")
                    continue

                filename = parts[1]

                try:
                    size = int(parts[2])
                except ValueError:
                    client.sendall(b"Invalid file size\n")
                    continue

                if size < 0:
                    client.sendall(b"Invalid file size\n")
                    continue

                if not valid_filename(filename):
                    client.sendall(b"Invalid filename\n")
                    continue

                filepath = os.path.join(STORAGE, filename)

                try:
                    with open(filepath, "xb") as output:
                        client.sendall(b"READY\n")
                        remaining = size

                        while remaining > 0:
                            chunk = file_stream.read(
                                min(65536, remaining)
                            )

                            if not chunk:
                                raise ConnectionError(
                                    "Upload interrupted"
                                )

                            output.write(chunk)
                            remaining -= len(chunk)

                    client.sendall(b"Upload complete\n")

                except FileExistsError:
                    client.sendall(b"File already exists\n")

                except (ConnectionError, OSError) as error:
                    print("Upload error:", error)
                    break

                continue

            elif message.upper().startswith("DOWNLOAD "):
                parts = message.split()

                if len(parts) != 2:
                    client.sendall(b"Use: DOWNLOAD filename\n")
                    continue

                filename = parts[1]

                if not valid_filename(filename):
                    client.sendall(b"Invalid filename\n")
                    continue

                filepath = os.path.join(STORAGE, filename)

                if not os.path.isfile(filepath):
                    client.sendall(b"File not found\n")
                    continue

                try:
                    size = os.path.getsize(filepath)

                    with open(filepath, "rb") as file:
                        client.sendall(
                            f"SIZE {size}\n".encode()
                        )

                        while True:
                            chunk = file.read(65536)

                            if not chunk:
                                break

                            client.sendall(chunk)

                    print("Download complete:", filename)

                except OSError as error:
                    print("Download error:", error)
                    break

                continue

            elif message.upper().startswith("DELETE "):
                parts = message.split()

                if len(parts) != 2:
                    client.sendall(b"Use: DELETE filename\n")
                    continue

                filename = parts[1]

                if not valid_filename(filename):
                    client.sendall(b"Invalid filename\n")
                    continue

                filepath = os.path.join(STORAGE, filename)

                if not os.path.isfile(filepath):
                    client.sendall(b"File not found\n")
                    continue

                try:
                    os.remove(filepath)
                    client.sendall(b"File deleted successfully\n")
                    print("Deleted:", filename)

                except OSError as error:
                    print("Delete error:", error)
                    client.sendall(b"Unable to delete file\n")

                continue

            else:
                response = "Dre Server received your message!"

            client.sendall((response + "\n").encode())

    finally:
        file_stream.close()
        client.close()
        print("Disconnected:", address)


server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", 5000))
server.listen()

print("Dre Server is running...")

while True:
    client, address = server.accept()

    thread = threading.Thread(
        target=handle_client,
        args=(client, address)
    )

    thread.start()

