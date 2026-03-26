import aiosqlite
from config import DB_PATH


async def get_db():
    return await aiosqlite.connect(DB_PATH)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_expire TEXT,
                joined_at TEXT DEFAULT (datetime('now')),
                last_active TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT DEFAULT 'video',
                caption TEXT,
                views INTEGER DEFAULT 0,
                added_at TEXT DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT,
                channel_link TEXT,
                channel_type TEXT DEFAULT 'public',
                added_at TEXT DEFAULT (datetime('now')),
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tariffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                price INTEGER NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tariff_id INTEGER,
                amount INTEGER NOT NULL,
                payment_type TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                confirmed_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        defaults = [
            ('sharing_enabled', '1'),
            ('premium_enabled', '1'),
            ('bot_name', 'Kinolar'),
            ('welcome_message', '👋 Assalomu alaykum {name} botimizga xush kelibsiz.\n\n🤝 Kino kodini yuboring.'),
            ('subscription_required', '1'),
            ('payment_card', ''),
            ('payment_note', 'To\'lovdan keyin chek yuboring.'),
        ]
        for key, val in defaults:
            await db.execute(
                'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                (key, val)
            )
        await db.commit()
        await cleanup_expired_premium(db)


async def cleanup_expired_premium(db=None):
    own = False
    if db is None:
        own = True
        db = await aiosqlite.connect(DB_PATH)
    await db.execute(
        """
        UPDATE users
        SET is_premium = 0
        WHERE is_premium = 1
          AND premium_expire IS NOT NULL
          AND premium_expire <= datetime('now')
        """
    )
    await db.commit()
    if own:
        await db.close()


async def compact_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await cleanup_expired_premium(db)
        await db.execute('VACUUM')
        await db.commit()


# users
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE user_id=?', (user_id,)) as cur:
            return await cur.fetchone()


async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)',
            (user_id, username, full_name),
        )
        await db.execute(
            'UPDATE users SET username=?, full_name=?, last_active=datetime(\'now\') WHERE user_id=?',
            (username, full_name, user_id),
        )
        await db.commit()


async def get_user_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cur:
            row = await cur.fetchone()
            return row[0]


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT user_id FROM users') as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def get_premium_user_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_premium=1 AND (premium_expire IS NULL OR premium_expire > datetime('now'))"
        ) as cur:
            row = await cur.fetchone()
            return row[0]


async def get_premium_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE is_premium=1 ORDER BY COALESCE(premium_expire, '9999-12-31') DESC"
        ) as cur:
            return await cur.fetchall()


async def set_premium(user_id: int, days: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        if days is None or int(days) <= 0:
            await db.execute(
                'UPDATE users SET is_premium=1, premium_expire=NULL WHERE user_id=?',
                (user_id,),
            )
        else:
            await db.execute(
                "UPDATE users SET is_premium=1, premium_expire=datetime('now', '+' || ? || ' days') WHERE user_id=?",
                (int(days), user_id),
            )
        await db.commit()


async def remove_premium(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET is_premium=0, premium_expire=NULL WHERE user_id=?', (user_id,))
        await db.commit()


async def is_premium_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE user_id=? AND is_premium=1 AND (premium_expire IS NULL OR premium_expire > datetime('now'))",
            (user_id,),
        ) as cur:
            return await cur.fetchone() is not None


# admins
async def is_admin(user_id: int):
    from config import SUPER_ADMIN_ID
    if user_id == SUPER_ADMIN_ID:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT 1 FROM admins WHERE user_id=?', (user_id,)) as cur:
            return await cur.fetchone() is not None


async def add_admin(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO admins (user_id, username, full_name) VALUES (?,?,?)',
            (user_id, username, full_name),
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM admins WHERE user_id=?', (user_id,))
        await db.commit()


async def get_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM admins ORDER BY added_at DESC') as cur:
            return await cur.fetchall()


# movies
async def add_movie(code: str, title: str, file_id: str, file_type: str, caption: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR REPLACE INTO movies (code, title, file_id, file_type, caption) VALUES (?,?,?,?,?)',
            (code, title, file_id, file_type, caption),
        )
        await db.commit()


async def get_movie(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM movies WHERE code=? AND is_active=1', (code,)) as cur:
            return await cur.fetchone()


async def get_all_movies():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM movies WHERE is_active=1 ORDER BY added_at DESC') as cur:
            return await cur.fetchall()


async def delete_movie(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE movies SET is_active=0 WHERE code=?', (code,))
        await db.commit()


async def increment_views(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE movies SET views=views+1 WHERE code=?', (code,))
        await db.commit()


async def get_movie_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM movies WHERE is_active=1') as cur:
            row = await cur.fetchone()
            return row[0] or 0


async def get_total_views():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT SUM(views) FROM movies WHERE is_active=1') as cur:
            row = await cur.fetchone()
            return row[0] or 0


async def update_movie(code: str, field: str, value: str):
    allowed = ['title', 'caption']
    if field not in allowed:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'UPDATE movies SET {field}=? WHERE code=?', (value, code))
        await db.commit()


# channels
async def add_channel(channel_id: str, name: str, link: str, ch_type: str = 'public'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO channels (channel_id, channel_name, channel_link, channel_type) VALUES (?,?,?,?)',
            (channel_id, name, link, ch_type),
        )
        await db.commit()


async def get_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM channels WHERE is_active=1 ORDER BY added_at DESC') as cur:
            return await cur.fetchall()


async def delete_channel(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE channels SET is_active=0 WHERE channel_id=?', (channel_id,))
        await db.commit()


# tariffs
async def add_tariff(name: str, duration: int, price: int, desc: str = ''):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO tariffs (name, duration_days, price, description) VALUES (?,?,?,?)',
            (name, duration, price, desc),
        )
        await db.commit()


async def get_tariffs(include_inactive: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = 'SELECT * FROM tariffs ORDER BY created_at DESC' if include_inactive else 'SELECT * FROM tariffs WHERE is_active=1 ORDER BY created_at DESC'
        async with db.execute(sql) as cur:
            return await cur.fetchall()


async def get_tariff(tariff_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM tariffs WHERE id=?', (tariff_id,)) as cur:
            return await cur.fetchone()


async def update_tariff(tariff_id: int, field: str, value):
    allowed = ['name', 'duration_days', 'price', 'is_active', 'description']
    if field not in allowed:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f'UPDATE tariffs SET {field}=? WHERE id=?', (value, tariff_id))
        await db.commit()


async def soft_delete_tariff(tariff_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE tariffs SET is_active=0 WHERE id=?', (tariff_id,))
        await db.commit()


# settings
async def get_setting(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT value FROM settings WHERE key=?', (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (key, value))
        await db.commit()
