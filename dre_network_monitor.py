import sqlite3
import csv
from pathlib import Path

DB_PATH = Path(__file__).with_name("networks_stats.db")

class NetworkMonitor:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.initialize_database()
    def connect(self):
        return sqlite3.connect(self.db_path)
    def initialize_database(self):
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS networks_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    role TEXT,
                    client_address TEXT,
                    event_type TEXT,
                    filename TEXT,
                    bytes_transferred INTEGER,
                    transfer_time REAL,
                    upload/download_speed REAL,
                    response_time REAL,
                    status TEXT
                )
            """)
    def record(self, role, client_address, event_type, filename = None, bytes_transferred = 0, duration = 0.0, response = None, status = "OK"):
        duration = max(float(duration), 0.000001)
        rate = (int(bytes_transferred) / duration) / (1024 * 1024)
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO networks_events (role, client_address, event_type, filename, bytes_transferred, transfer_time, upload/download_speed, response_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (role, client_address, event_type, filename, int(bytes_transferred), float(duration), rate, response, status))

    def export_csv(self, output = "networks_stats.csv"):
        with self.connect() as connection:
            cursor = connection.execute("""
                SELECT timestamp, role, client_address, event_type, filename, bytes_transferred, transfer_time, upload/download_speed, response_time, status
                FROM networks_events
                ORDER BY id
            """)
            rows = cursor.fetchall()
            headers = [column[0] for column in cursor.description]
            with open(output, "w", newline = "", encoding = "utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerows(rows)
            return len(rows)

    def summary(self):
        with self.connect() as connection:
            return connection.execute("""
                SELECT event_type, COUNT(*), AVG(upload/download_speed), AVG(transfer_time), AVG(response_time), SUM(bytes_transferred)
                    FROM networks_events
                    GROUP BY event_type
                """).fetchall()