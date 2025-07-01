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
    """Initializes the database and creates the 'managers' table if it doesn't exist."""
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