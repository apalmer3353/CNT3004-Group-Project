# Dre Server Setup

## Requirements
- Python 3
- Server and client computers on the same network

## Start the Server

1. Open Terminal in the project folder.
2. Make sure server.crt and its matching server.key are present.
3. Run `python3 create_user.py` to create login credentials if server_users.json does not exist.
4. Run `python3 dre_server.py`.

The server listens on port 5000.

## Supported Commands
- DIR - List stored files
- UPLOAD - Upload a file
- DOWNLOAD - Download a file
- DELETE - Delete a file
- MKDIR - Create a folder
- RMDIR - Remove a folder

## Security
- TLS encryption is enabled.
- Users must log in before sending commands.
- Private keys and login credentials are not uploaded to GitHub.
- Clients must trust the server's current certificate.
- Generate a new certificate/key pair if hosting on another computer.

## Testing
Local TLS connections, login authentication, and incorrect-password rejection have been tested.

Connections from a separate computer still need testing.

## Commands for the Client

After logging in, the client can send these commands:

- DIR - Shows the files on the server.
- UPLOAD filename size - Uploads a file.
- DOWNLOAD filename - Downloads a file.
- DELETE filename - Deletes a file.
- MKDIR foldername - Makes a folder.
- RMDIR foldername - Deletes an empty folder.

For DIR, the server sends DIR and the number of files first.
The client then reads that many filenames.

If a file already exists during an upload, the server asks
OVERWRITE? and the client answers YES or NO.

The server sends READY when it is ready for the upload.

## Testing With Clients

I tested two clients connected to the server at the same time
on my Mac, and both worked.

We still need to test everything using three separate computers
when the group puts everything together.
