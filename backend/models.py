import oracledb
from flask import g, current_app
import os

# Global variable for connection pool
pool = None

def init_db_connection(app):
    
    """Initialize the database connection pool."""
    global pool
    try:
        pool = oracledb.create_pool(
            user=app.config['DB_USERNAME'],
            password=app.config['DB_PASSWORD'],
            dsn=app.config['DB_DSN'],
            min=2, # Minimum number of connections in the pool
            max=5, # Maximum number of connections in the pool
            increment=1, # Number of connections to increment by if more are needed
        )
        print("Database connection pool created successfully.")
    except oracledb.Error as e:
        print(f"Error creating database connection pool: {e}")
        # Consider exiting or raising an exception if DB connection is critical
        # raise # Uncomment to stop the app if pool creation fails

def get_db():
    """Get a database connection from the pool."""
    if 'db' not in g:
        if pool:
            try:
                g.db = pool.acquire()
            except oracledb.Error as e:
                print(f"Error acquiring connection from pool: {e}")
                raise # Or handle more gracefully
        else:
            # Fallback or error if pool not initialized
            print("Database pool not initialized. Cannot acquire connection.")
            raise RuntimeError("Database pool not initialized.")
    return g.db

def close_db(e=None):
    """Close the database connection."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except oracledb.Error as e:
            print(f"Error closing database connection: {e}")


def query_db(query, args=(), one=False, commit=False, is_ddl=False):
    """Executes a query and returns results.
       Handles DML (commit=True) and DDL (is_ddl=True).
    """
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # print(f"Executing query: {query} with args: {args}") # For debugging

        if is_ddl: # For DDL statements like CREATE, ALTER, DROP
            cursor.execute(query) # DDL statements don't take args usually
            conn.commit() # DDL typically implies commit
            return None

        cursor.execute(query, args)

        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            if commit:
                conn.commit()
            # For INSERT returning ID, use:
            # cursor.execute("INSERT ... RETURNING id INTO :out_id", out_id=cursor.var(oracledb.NUMBER))
            # return cursor.getvalue(out_id)[0]
            return cursor.rowcount # Number of rows affected
        else: # SELECT
            columns = [col[0].lower() for col in cursor.description]
            rv = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return (rv[0] if rv else None) if one else rv
    except oracledb.Error as e:
        print(f"Database error: {e}")
        if conn and query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            conn.rollback() # Rollback on error for DML
        raise # Re-raise the exception to be handled by the caller
    finally:
        if cursor:
            cursor.close()
        # Connection is closed by close_db via app context teardown


# --- Application Specific Database Functions ---

def get_all_meetings_with_items(search_term=None, start_date=None, end_date=None):
    base_query = """
        SELECT
            m.meeting_id,
            m.title,
            m.meeting_instance,
            TO_CHAR(m.meeting_date, 'YYYY-MM-DD') as meeting_date_str, -- Format for consistency
            m.created_at,
            m.uploaded_by
        FROM MEETINGS m
    """
    conditions = []
    params = {}

    if search_term:
        conditions.append("(LOWER(m.title) LIKE :search_term OR LOWER(m.meeting_instance) LIKE :search_term)")
        params['search_term'] = f"%{search_term.lower()}%"

    if start_date:
        conditions.append("TRUNC(m.meeting_date) >= TO_DATE(:start_date, 'YYYY-MM-DD')")
        params['start_date'] = start_date
    
    if end_date:
        conditions.append("TRUNC(m.meeting_date) <= TO_DATE(:end_date, 'YYYY-MM-DD')")
        params['end_date'] = end_date

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY m.created_at DESC, m.meeting_id DESC" #ล่าสุดขึ้นก่อน

    meetings = query_db(base_query, params)
    if meetings is None: # query_db might raise an error before returning None if there's a DB issue
        return []

    for meeting in meetings:
        items_query = """
            SELECT item_id, item_number, original_filename, stored_filename, filesize, agenda_title_th
            FROM AGENDA_ITEMS
            WHERE meeting_id = :meeting_id
            ORDER BY item_number ASC
        """
        meeting['agenda_items'] = query_db(items_query, {'meeting_id': meeting['meeting_id']})
    return meetings

def create_meeting_and_agendas(title, instance, date, username, agenda_files_info):
    """
    agenda_files_info: list of dicts [{ 'item_number': X, 'original_filename': Y, 'stored_filename': Z, 'file_path': P, 'filesize': S}, ...]
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Create Meeting
        meeting_sql = """
        INSERT INTO MEETINGS (title, meeting_instance, meeting_date, uploaded_by)
        VALUES (:title, :instance, TO_DATE(:mdate, 'YYYY-MM-DD'), :username)
        RETURNING meeting_id INTO :new_meeting_id
        """
        new_meeting_id_var = cursor.var(oracledb.NUMBER)
        cursor.execute(meeting_sql, {
            'title': title,
            'instance': instance,
            'mdate': date,
            'username': username,
            'new_meeting_id': new_meeting_id_var
        })
        meeting_id = new_meeting_id_var.getvalue()[0]

        # 2. Create Agenda Items
        agenda_sql = """
        INSERT INTO AGENDA_ITEMS (meeting_id, item_number, original_filename, stored_filename, file_url, filesize)
        VALUES (:meeting_id, :item_number, :original_filename, :stored_filename, :file_url, :filesize)
        """
        for item in agenda_files_info:
            cursor.execute(agenda_sql, {
                'meeting_id': meeting_id,
                'item_number': item['item_number'],
                'original_filename': item['original_filename'],
                'stored_filename': item['stored_filename'],
                'file_url': item['file_url'],
                'filesize': item['filesize']
            })
        conn.commit()
        return meeting_id
    except oracledb.Error as e:
        conn.rollback()
        print(f"Error in create_meeting_and_agendas: {e}")
        raise
    finally:
        if cursor:
            cursor.close()

def get_meeting_by_id(meeting_id):
    return query_db("SELECT * FROM MEETINGS WHERE meeting_id = :id", {'id': meeting_id}, one=True)

def get_agenda_items_for_meeting(meeting_id):
     return query_db("SELECT * FROM AGENDA_ITEMS WHERE meeting_id = :id ORDER BY item_number", {'id': meeting_id})

def get_agenda_item_by_id(item_id):
    return query_db("SELECT * FROM AGENDA_ITEMS WHERE item_id = :id", {'id': item_id}, one=True)

def delete_meeting_from_db(meeting_id):
    # ON DELETE CASCADE should handle agenda_items
    # First, get associated files to delete them from filesystem
    items = get_agenda_items_for_meeting(meeting_id)
    try:
        query_db("DELETE FROM MEETINGS WHERE meeting_id = :id", {'id': meeting_id}, commit=True)
        return items # Return items so their files can be deleted
    except oracledb.Error as e:
        print(f"Error deleting meeting {meeting_id}: {e}")
        raise
    return []


def delete_agenda_item_from_db(item_id):
    item = get_agenda_item_by_id(item_id)
    if not item:
        return None # Item not found
    try:
        query_db("DELETE FROM AGENDA_ITEMS WHERE item_id = :id", {'id': item_id}, commit=True)
        return item # Return item so its file can be deleted
    except oracledb.Error as e:
        print(f"Error deleting agenda item {item_id}: {e}")
        raise
    return None

def get_next_agenda_item_number(meeting_id):
    """Determines the next available agenda item number for a given meeting.
       If items are 1, 2, 4, this should return 3. If 1, 2, 3, returns 4.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Find existing item numbers for the meeting
        cursor.execute("""
            SELECT item_number
            FROM AGENDA_ITEMS
            WHERE meeting_id = :meeting_id
            ORDER BY item_number ASC
        """, {'meeting_id': meeting_id})
        
        existing_numbers = [row[0] for row in cursor.fetchall()]
        
        if not existing_numbers:
            return 1 # No items yet, start with 1
        
        # Check for gaps
        expected_number = 1
        for num in existing_numbers:
            if num != expected_number:
                return expected_number # Found a gap
            expected_number += 1
        
        return expected_number # No gaps, so return the next number in sequence
        
    except oracledb.Error as e:
        print(f"Error getting next agenda item number: {e}")
        raise
    finally:
        if cursor:
            cursor.close()

def get_next_agenda_item_number_for_form():
    """
    This function is tricky because it depends on the current state of the form *before* submission.
    The JavaScript on the frontend should manage displaying the "next" number when items are added/removed from the form.
    When submitting, the backend can re-verify these numbers or use the logic in `get_next_agenda_item_number`
    if the frontend doesn't send explicit numbers or if an item was deleted from an *existing* meeting.

    For a *new* meeting being created, the frontend JS can just increment.
    If an admin *edits* an existing meeting and deletes item 3, then adds a new one,
    the backend should ideally assign it as item 3.
    The current `create_meeting_and_agendas` expects `item_number` to be provided.
    The frontend JS should calculate this.
    """
    # This is more of a placeholder, actual logic will be in JS and backend processing of form.
    return 1 # Default for a new item in a new meeting.