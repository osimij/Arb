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
    
    # Create the managers table with user_id column
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            assignment_count INTEGER DEFAULT 0
        )
        """
    )
    
    # Check if user_id column exists, if not add it (for existing databases)
    cursor.execute("PRAGMA table_info(managers)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_id' not in columns:
        cursor.execute("ALTER TABLE managers ADD COLUMN user_id INTEGER")
    
    db.commit()

def add_manager(username, user_id=None):
    """Adds a new manager to the database with optional user_id."""
    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("INSERT INTO managers (username, user_id) VALUES (?, ?)", (username, user_id))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        # This error occurs if the username is already in the database (UNIQUE constraint)
        return False

def update_manager_user_id(username, user_id):
    """Updates the user_id for an existing manager."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE managers SET user_id = ? WHERE username = ?", (user_id, username))
    db.commit()
    return cursor.rowcount > 0

def delete_manager(username):
    """Deletes a manager from the database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM managers WHERE username = ?", (username,))
    db.commit()
    return cursor.rowcount > 0

def get_all_managers():
    """Retrieves all manager usernames from the database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM managers ORDER BY id")
    return [row["username"] for row in cursor.fetchall()]

def get_all_managers_with_ids():
    """Retrieves all managers with their user IDs from the database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username, user_id FROM managers WHERE user_id IS NOT NULL ORDER BY id")
    return [(row["username"], row["user_id"]) for row in cursor.fetchall()]

def get_manager_user_id(username):
    """Get the user_id for a specific manager."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT user_id FROM managers WHERE username = ?", (username,))
    result = cursor.fetchone()
    return result["user_id"] if result else None

def is_manager_by_user_id(user_id):
    """Check if a user_id belongs to a manager."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM managers WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result["username"] if result else None

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