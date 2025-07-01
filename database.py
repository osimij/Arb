import sqlite3
import threading

DATABASE_FILE = "bot_database.db"

# Thread-local data to ensure thread safety for database connections
local = threading.local()

def get_db():
    """Opens a new database connection if there is none yet for the current thread."""
    if not hasattr(local, "db"):
        local.db = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        local.db.row_factory = sqlite3.Row
    return local.db

def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = getattr(local, "db", None)
    if db is not None:
        db.close()
        local.db = None

def init_db():
    """Initializes the database and creates the 'managers' and 'api_keys' tables if they don't exist."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            assignment_count INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_username TEXT UNIQUE NOT NULL,
            api_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manager_username) REFERENCES managers (username) ON DELETE CASCADE
        )
        """
    )
    db.commit()

def add_manager(username):
    """Adds a new manager to the database."""
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("INSERT INTO managers (username) VALUES (?)", (username,))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        # This error occurs if the username is already in the database (UNIQUE constraint)
        return False

def delete_manager(username):
    """Deletes a manager from the database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM managers WHERE username = ?", (username,))
    db.commit()
    return cursor.rowcount > 0

def get_all_managers():
    """Retrieves all managers from the database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM managers ORDER BY id")
    return [row["username"] for row in cursor.fetchall()]

def get_next_manager():
    """
    Retrieves the next manager for assignment using round-robin logic.
    This ensures an equal distribution of users to managers.
    """
    db = get_db()
    cursor = db.cursor()

    # Find the manager with the lowest assignment_count
    cursor.execute(
        "SELECT id, username FROM managers ORDER BY assignment_count ASC, id ASC LIMIT 1"
    )
    manager = cursor.fetchone()

    if manager:
        # Increment their assignment_count
        cursor.execute(
            "UPDATE managers SET assignment_count = assignment_count + 1 WHERE id = ?",
            (manager["id"],),
        )
        db.commit()
        return manager["username"]

    return None


def add_api_key(manager_username, api_key):
    """Adds or updates an API key for a manager."""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO api_keys (manager_username, api_key) VALUES (?, ?)",
            (manager_username, api_key)
        )
        db.commit()
        return True
    except sqlite3.Error:
        return False


def get_api_key(manager_username):
    """Retrieves the API key for a specific manager."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT api_key FROM api_keys WHERE manager_username = ?", (manager_username,))
    result = cursor.fetchone()
    return result["api_key"] if result else None


def delete_api_key(manager_username):
    """Deletes the API key for a specific manager."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM api_keys WHERE manager_username = ?", (manager_username,))
    db.commit()
    return cursor.rowcount > 0


def get_managers_with_api_keys():
    """Retrieves all managers who have API keys."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT m.username, ak.api_key, ak.created_at 
        FROM managers m 
        JOIN api_keys ak ON m.username = ak.manager_username 
        ORDER BY m.id
        """
    )
    return [{"username": row["username"], "api_key": row["api_key"], "created_at": row["created_at"]} 
            for row in cursor.fetchall()] 