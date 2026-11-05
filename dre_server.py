

import socket
import threading
import os

os.makedirs("server_storage", exist_ok=True)

def handle_client(client, address):
    print("Connected to:", address)

    while True:
        data = client.recv(1024)

        if not data:
            break

        message = data.decode().strip()
        print("Command:", message)

        if message.upper() == "DIR":
            files = os.listdir("server_storage")
            response = "\n".join(files) if files else "Folder is empty"

        elif message.upper().startswith("UPLOAD "):
            filename = message[7:].strip()

            if not filename or os.path.basename(filename) != filename:
                response = "Invalid filename"
            elif os.path.exists("server_storage/" + filename):
                response = "File already exists"
            else:
                response = "Ready to upload: " + filename

        else:
            response = "Dre Server received your message!"

        client.sendall((response + "\n").encode())

    client.close()
    print("Disconnected:", address)

server = socket.socket()
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

