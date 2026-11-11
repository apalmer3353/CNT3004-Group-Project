import socket
import threading
import os

STORAGE = "server_storage"
os.makedirs(STORAGE, exist_ok=True)


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

                if (filename in (".", "..")
                        or os.path.basename(filename) != filename
                        or "/" in filename
                        or "\\" in filename):
                    client.sendall(b"Invalid filename\n")
                    continue

                filepath = os.path.join(STORAGE, filename)

                try:
                    with open(filepath, "xb") as output:
                        client.sendall(b"READY\n")

                        remaining = size

                        while remaining > 0:
                            chunk = file_stream.read(min(65536, remaining))

                            if not chunk:
                                raise ConnectionError("Upload interrupted")

                            output.write(chunk)
                            remaining -= len(chunk)

                    client.sendall(b"Upload complete\n")

                except FileExistsError:
                    client.sendall(b"File already exists\n")

                except (ConnectionError, OSError) as error:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    print("Upload error:", error)
                    break

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
