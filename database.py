import sqlite3
from datetime import datetime, timedelta


DATABASE = "valorant_bot.db"

PARTY_EXPIRY_MINUTES = 15
REQUEST_COOLDOWN_SECONDS = 30


def connect():
    return sqlite3.connect(DATABASE)


def now():
    return datetime.utcnow()


# =========================================================
# DATABASE
# =========================================================

def create_database():

    conn = connect()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            rank TEXT,
            is_active INTEGER DEFAULT 1,
            is_banned INTEGER DEFAULT 0,
            last_request_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # PARTIES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_telegram_id INTEGER NOT NULL,
            required_rank TEXT NOT NULL,
            players_needed INTEGER NOT NULL,
            party_code TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL
        )
    """)

    # MATCHES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS party_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            user_telegram_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            notified_at TEXT NOT NULL,
            responded_at TEXT,
            UNIQUE(party_id, user_telegram_id)
        )
    """)

    # ADMIN MESSAGES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            answered INTEGER DEFAULT 0
        )
    """)

    conn.commit()

    # Migration دیتابیس‌های قدیمی
    add_column_if_missing(
        cursor,
        "users",
        "is_banned",
        "INTEGER DEFAULT 0"
    )

    add_column_if_missing(
        cursor,
        "users",
        "last_request_at",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "party_matches",
        "status",
        "TEXT DEFAULT 'pending'"
    )

    add_column_if_missing(
        cursor,
        "party_matches",
        "responded_at",
        "TEXT"
    )

    conn.commit()
    conn.close()


def add_column_if_missing(
    cursor,
    table,
    column,
    definition
):

    cursor.execute(
        f"PRAGMA table_info({table})"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if column not in columns:

        cursor.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )


# =========================================================
# USERS
# =========================================================

def save_user(telegram_id, username):

    conn = connect()
    cursor = conn.cursor()

    current = now().isoformat()

    cursor.execute("""
        INSERT INTO users
        (
            telegram_id,
            username,
            is_active,
            is_banned,
            created_at,
            updated_at
        )
        VALUES (?, ?, 1, 0, ?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username = excluded.username,
            is_active = 1,
            updated_at = excluded.updated_at
    """, (
        telegram_id,
        username,
        current,
        current
    ))

    conn.commit()
    conn.close()


def save_rank(telegram_id, rank):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET rank = ?,
            updated_at = ?
        WHERE telegram_id = ?
    """, (
        rank,
        now().isoformat(),
        telegram_id
    ))

    conn.commit()
    conn.close()


def get_user(telegram_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            telegram_id,
            username,
            rank,
            is_active,
            last_request_at,
            is_banned
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    result = cursor.fetchone()

    conn.close()

    return result


def get_all_users():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            telegram_id,
            username,
            rank,
            is_active,
            is_banned
        FROM users
        ORDER BY id DESC
    """)

    results = cursor.fetchall()

    conn.close()

    return results


def get_rank(telegram_id):

    user = get_user(telegram_id)

    if user:
        return user[2]

    return None


def is_banned(telegram_id):

    user = get_user(telegram_id)

    if user:
        return bool(user[5])

    return False


def ban_user(telegram_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_banned = 1,
            is_active = 0,
            updated_at = ?
        WHERE telegram_id = ?
    """, (
        now().isoformat(),
        telegram_id
    ))

    conn.commit()
    conn.close()


def unban_user(telegram_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_banned = 0,
            is_active = 1,
            updated_at = ?
        WHERE telegram_id = ?
    """, (
        now().isoformat(),
        telegram_id
    ))

    conn.commit()
    conn.close()


def set_user_active(
    telegram_id,
    active=True
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_active = ?
        WHERE telegram_id = ?
    """, (
        1 if active else 0,
        telegram_id
    ))

    conn.commit()
    conn.close()


# =========================================================
# REQUEST COOLDOWN
# =========================================================

def get_last_request_time(telegram_id):

    user = get_user(telegram_id)

    if user:
        return user[4]

    return None


def can_create_request(telegram_id):

    last_request = get_last_request_time(
        telegram_id
    )

    if not last_request:
        return True, 0

    try:

        last_time = datetime.fromisoformat(
            last_request
        )

        elapsed = (
            now() - last_time
        ).total_seconds()

        if elapsed >= REQUEST_COOLDOWN_SECONDS:
            return True, 0

        remaining = int(
            REQUEST_COOLDOWN_SECONDS - elapsed
        )

        return False, remaining

    except Exception:

        return True, 0


def update_last_request_time(telegram_id):

    conn = connect()
    cursor = conn.cursor()

    current = now().isoformat()

    cursor.execute("""
        UPDATE users
        SET last_request_at = ?,
            updated_at = ?
        WHERE telegram_id = ?
    """, (
        current,
        current,
        telegram_id
    ))

    conn.commit()
    conn.close()


# =========================================================
# PARTIES
# =========================================================

def create_party(
    creator_id,
    required_rank,
    players_needed,
    party_code
):

    conn = connect()
    cursor = conn.cursor()

    current = now().isoformat()

    cursor.execute("""
        INSERT INTO parties
        (
            creator_telegram_id,
            required_rank,
            players_needed,
            party_code,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, 'active', ?)
    """, (
        creator_id,
        required_rank,
        players_needed,
        party_code,
        current
    ))

    party_id = cursor.lastrowid

    conn.commit()
    conn.close()

    update_last_request_time(
        creator_id
    )

    return party_id


def get_party(party_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            creator_telegram_id,
            required_rank,
            players_needed,
            party_code,
            status,
            created_at
        FROM parties
        WHERE id = ?
    """, (party_id,))

    result = cursor.fetchone()

    conn.close()

    return result


def get_active_party(creator_id):

    expire_old_parties()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            required_rank,
            players_needed,
            party_code,
            status,
            created_at
        FROM parties
        WHERE creator_telegram_id = ?
        AND status = 'active'
        ORDER BY id DESC
        LIMIT 1
    """, (creator_id,))

    result = cursor.fetchone()

    conn.close()

    return result


def cancel_active_party(creator_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE parties
        SET status = 'cancelled'
        WHERE creator_telegram_id = ?
        AND status = 'active'
    """, (creator_id,))

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0


def expire_old_parties():

    conn = connect()
    cursor = conn.cursor()

    expiration = (
        now()
        - timedelta(minutes=PARTY_EXPIRY_MINUTES)
    ).isoformat()

    cursor.execute("""
        UPDATE parties
        SET status = 'expired'
        WHERE status = 'active'
        AND created_at < ?
    """, (expiration,))

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed


def get_active_parties_for_rank(
    required_rank
):

    expire_old_parties()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            creator_telegram_id,
            required_rank,
            players_needed,
            party_code,
            created_at
        FROM parties
        WHERE required_rank = ?
        AND status = 'active'
        ORDER BY id ASC
    """, (required_rank,))

    results = cursor.fetchall()

    conn.close()

    return results


def get_all_active_parties():

    expire_old_parties()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            creator_telegram_id,
            required_rank,
            players_needed,
            party_code,
            status,
            created_at
        FROM parties
        WHERE status = 'active'
        ORDER BY id DESC
    """)

    results = cursor.fetchall()

    conn.close()

    return results


def admin_cancel_party(party_id):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE parties
        SET status = 'cancelled'
        WHERE id = ?
        AND status = 'active'
    """, (party_id,))

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0


# =========================================================
# MATCHMAKING
# =========================================================

def get_matching_users(
    required_rank,
    creator_id,
    limit
):

    expire_old_parties()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            telegram_id,
            username
        FROM users
        WHERE rank = ?
        AND telegram_id != ?
        AND is_active = 1
        AND is_banned = 0
        LIMIT ?
    """, (
        required_rank,
        creator_id,
        limit
    ))

    results = cursor.fetchall()

    conn.close()

    return results


def get_available_users_for_party(
    required_rank,
    creator_id,
    party_id,
    limit
):

    expire_old_parties()

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.telegram_id,
            u.username,
            u.rank
        FROM users u
        WHERE u.rank = ?
        AND u.telegram_id != ?
        AND u.is_active = 1
        AND u.is_banned = 0

        AND NOT EXISTS (
            SELECT 1
            FROM party_matches pm
            WHERE pm.party_id = ?
            AND pm.user_telegram_id = u.telegram_id
        )

        AND NOT EXISTS (
            SELECT 1
            FROM party_matches pm2
            JOIN parties p
                ON p.id = pm2.party_id
            WHERE pm2.user_telegram_id = u.telegram_id
            AND pm2.status = 'accepted'
            AND p.status = 'active'
        )

        LIMIT ?
    """, (
        required_rank,
        creator_id,
        party_id,
        limit
    ))

    results = cursor.fetchall()

    conn.close()

    return results


def add_party_match(
    party_id,
    user_id
):

    conn = connect()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO party_matches
            (
                party_id,
                user_telegram_id,
                status,
                notified_at
            )
            VALUES (?, ?, 'pending', ?)
        """, (
            party_id,
            user_id,
            now().isoformat()
        ))

        conn.commit()

        success = True

    except sqlite3.IntegrityError:

        success = False

    conn.close()

    return success


def get_match(
    party_id,
    user_id
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            party_id,
            user_telegram_id,
            status,
            notified_at,
            responded_at
        FROM party_matches
        WHERE party_id = ?
        AND user_telegram_id = ?
    """, (
        party_id,
        user_id
    ))

    result = cursor.fetchone()

    conn.close()

    return result


def set_match_status(
    party_id,
    user_id,
    status
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE party_matches
        SET status = ?,
            responded_at = ?
        WHERE party_id = ?
        AND user_telegram_id = ?
    """, (
        status,
        now().isoformat(),
        party_id,
        user_id
    ))

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0


def count_accepted_players(
    party_id
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM party_matches
        WHERE party_id = ?
        AND status = 'accepted'
    """, (party_id,))

    result = cursor.fetchone()[0]

    conn.close()

    return result


def count_pending_players(
    party_id
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM party_matches
        WHERE party_id = ?
        AND status = 'pending'
    """, (party_id,))

    result = cursor.fetchone()[0]

    conn.close()

    return result


def mark_party_filled(
    party_id
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE parties
        SET status = 'filled'
        WHERE id = ?
    """, (party_id,))

    conn.commit()
    conn.close()


# =========================================================
# ADMIN MESSAGES
# =========================================================

def save_admin_message(
    user_id,
    message_text
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO admin_messages
        (
            user_telegram_id,
            message_text,
            created_at,
            answered
        )
        VALUES (?, ?, ?, 0)
    """, (
        user_id,
        message_text,
        now().isoformat()
    ))

    message_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return message_id


def get_admin_messages():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            user_telegram_id,
            message_text,
            created_at,
            answered
        FROM admin_messages
        WHERE answered = 0
        ORDER BY id DESC
    """)

    results = cursor.fetchall()

    conn.close()

    return results


def mark_admin_message_answered(
    message_id
):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE admin_messages
        SET answered = 1
        WHERE id = ?
    """, (message_id,))

    conn.commit()
    conn.close()


# =========================================================
# STATISTICS
# =========================================================

def get_statistics():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )
    total_users = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE is_banned = 1
    """)
    banned_users = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM parties
        WHERE status = 'active'
    """)
    active_parties = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM parties
    """)
    total_parties = cursor.fetchone()[0]

    conn.close()

    return (
        total_users,
        banned_users,
        active_parties,
        total_parties
    )