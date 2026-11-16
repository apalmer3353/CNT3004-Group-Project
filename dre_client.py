"""Starts the Dre file sharing client. Run: python dre_client.py [server_ip] [port]"""

import socket
import ssl
import sys

from dre_client_connection import ClientError, DreClient
from dre_client_ui import run_command


def main():
    client = DreClient()
    print("Dre File Sharing Client - type 'help' for commands")

    # Connect right away if an IP was given
    if len(sys.argv) > 1:
        try:
            run_command(client, "connect " + " ".join(sys.argv[1:]))
        except (ClientError, OSError) as error:
            print(f"Error: {error}")

    while True:
        try:
            line = input("dre> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        try:
            if not run_command(client, line):
                break
        except ClientError as error:
            print(f"Error: {error}")
        except (ConnectionError, socket.timeout, TimeoutError, ssl.SSLError,
                OSError) as error:
            # Connection is unusable after a network error
            print(f"\nConnection lost: {error}")
            client.disconnect()
        except KeyboardInterrupt:
            # Ctrl+C mid-transfer breaks the stream
            print("\nOperation cancelled - disconnecting")
            client.disconnect()

    client.disconnect()
    print("Goodbye")


if __name__ == "__main__":
    main()
