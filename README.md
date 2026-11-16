# CNT3004 Dre File Sharing System

A socket-based file sharing system in Python. The server runs on one computer and the clients connect to it from other computers over TLS.

## Files

| File | Purpose |
| --- | --- |
| `dre_server.py` | Multithreaded server (port 5000) |
| `create_user.py` | Creates the server login (`server_users.json`) |
| `dre_client.py` | Starts the client |
| `dre_client_connection.py` | Client sockets, TLS, login and file transfers |
| `dre_client_ui.py` | Client commands, prompts and progress bars |
| `dre_network_monitor.py` | Saves performance statistics to `networks_stats.db` |
| `dre_analyze_stats.py` | Prints a statistics summary and exports CSV |

## Requirements

- Python 3 (no extra packages)
- All computers on the same private network (a phone hotspot works, campus Wi-Fi does not)

## Server Setup

1. Put `server.crt` and its matching `server.key` in the server folder.
2. Create the login (first time only):
   ```
   python create_user.py
   ```
3. Start the server:
   ```
   python dre_server.py
   ```
4. Find the server's IP address (`ipconfig` on Windows, `ifconfig` on Mac). Clients need it.
5. If the firewall asks, allow Python on private networks.

## Client Setup

1. Put these files in one folder on each client computer:
   - `dre_client.py`
   - `dre_client_connection.py`
   - `dre_client_ui.py`
   - `dre_network_monitor.py`
   - `server.crt` (copied from the server, **not** `server.key`)
2. Start the client:
   ```
   python dre_client.py
   ```
   Or connect right away:
   ```
   python dre_client.py <server_ip> 5000
   ```

## Client Commands

| Command | Description |
| --- | --- |
| `connect <server_ip> [port]` | Connect and log in (port defaults to 5000) |
| `dir` | List files and folders on the server |
| `upload <local_path>` | Upload a file; asks before overwriting an existing one |
| `download <filename>` | Download a file into `./downloads` |
| `delete <filename>` | Delete a file on the server |
| `subfolder create <name>` | Create a folder on the server |
| `subfolder delete <name>` | Delete an empty folder on the server |
| `disconnect` | Close the connection |
| `help` | Show the command list |
| `quit` | Exit the client |

### Example Session (your numbers will vary)

```
dre> connect 192.168.1.20 5000
Connected to 192.168.1.20:5000 over TLS (3.1 ms)
Username: dre_admin
Password:
Login successful
dre> subfolder create videos
Folder created successfully
dre> upload sample_video.mp4
  [#########################] 100%  2,048.0/2,048.0 MB
Upload complete: 2,048.00 MB in 41.20 s (49.71 MB/s)
dre> dir
2 item(s) on server:
  sample_video.mp4
  videos
dre> download sample_video.mp4
  [#########################] 100%  2,048.0/2,048.0 MB
Saved to downloads/sample_video.mp4: 2,048.00 MB in 38.90 s (52.65 MB/s)
dre> quit
Goodbye
```

## Protocol

Commands are text lines ending in `\n`, sent over a TLS connection.

| Client sends | Server replies |
| --- | --- |
| *(on connect)* | `Username:` then `Password:` then `Login successful` or `Login failed` |
| `DIR` | `DIR <count>` followed by one name per line |
| `UPLOAD <name> <size>` | `OVERWRITE?` (client answers `YES`/`NO`) or `READY`; after the bytes: `Upload complete` |
| `DOWNLOAD <name>` | `SIZE <bytes>` followed by the file data, or `File not found` |
| `DELETE <name>` | `File deleted successfully`, `File not found`, or `File is currently being processed` |
| `MKDIR <name>` | `Folder created successfully` or `Folder already exists` |
| `RMDIR <name>` | `Folder deleted successfully` or `Folder not found` |

## Security

- All traffic, including the password, is encrypted with TLS.
- Passwords are stored on the server as salted PBKDF2-SHA256 hashes, never as plain text.
- The client trusts only the server's own `server.crt`, so a different server can't pretend to be it.
- `server.key` and `server_users.json` are in `.gitignore` and must never be pushed to GitHub.

## Performance Statistics

Every client operation is timed and saved to `networks_stats.db` with:

- transfer rate (MB/s)
- transfer time (seconds)
- response time (ms, from sending a command to the first reply)
- status (`OK`, `ERROR`, `FAILED`, `INTERRUPTED`)

View a summary or export to CSV for the report:
```
python dre_analyze_stats.py
python dre_analyze_stats.py --csv results.csv
```

## Limitations

- Filenames and folder names can't contain spaces or `/` (so no nested paths like `a/b`).
- Interrupted downloads restart from the beginning (resume is not implemented yet).
- The TLS certificate expires December 12, 2026. Regenerate it if needed.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Connection refused` | Server isn't running, or the IP/port is wrong |
| `Timed out connecting` | Firewall is blocking port 5000, or computers aren't on the same network |
| `TLS failed (CERTIFICATE_VERIFY_FAILED)` | The client's `server.crt` doesn't match the server's; copy it again |
| `Missing server.crt` | Copy `server.crt` from the server into the client folder |
| `Login failed` | Wrong username/password; rerun `create_user.py` on the server if needed |
