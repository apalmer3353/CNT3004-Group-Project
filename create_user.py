import hashlib
import json
import os
import getpass

username = "dre_admin"

password = getpass.getpass("Create password: ")
confirm = getpass.getpass("Confirm password: ")

if not password or password != confirm:
    raise SystemExit("Passwords do not match.")

salt = os.urandom(16)
iterations = 600000

password_hash = hashlib.pbkdf2_hmac(
    "sha256",
    password.encode(),
    salt,
    iterations
)

users = {
    username: {
        "salt": salt.hex(),
        "hash": password_hash.hex(),
        "iterations": iterations
    }
}

with open("server_users.json", "x") as file:
    json.dump(users, file, indent=4)

os.chmod("server_users.json", 0o600)

print("User credentials created successfully!")
