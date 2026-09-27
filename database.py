import sqlite3

class Database:
    def __init__(self, db_file="bot_database.db"):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, name TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS channels (channel_id INTEGER PRIMARY KEY, channel_link TEXT, channel_name TEXT)")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                movie_id INTEGER PRIMARY KEY,
                title TEXT,
                description TEXT,
                duration TEXT,
                year TEXT,
                views INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                rating_count INTEGER DEFAULT 0
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS movie_parts (
                part_id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER,
                part_number INTEGER,
                file_id TEXT,
                FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE
            )
        """)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, movie_id INTEGER, PRIMARY KEY (user_id, movie_id))")
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_id INTEGER,
                search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER,
                user_id INTEGER,
                rating INTEGER,
                comment TEXT
            )
        """)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('sub_status', 'ON')")
        self.connection.commit()

    def add_user(self, user_id, username):
        self.cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        self.connection.commit()

    def get_all_users(self):
        self.cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in self.cursor.fetchall()]

    def get_user_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]

    def add_admin(self, user_id, name):
        self.cursor.execute("INSERT OR REPLACE INTO admins (user_id, name) VALUES (?, ?)", (user_id, name))
        self.connection.commit()

    def remove_admin(self, user_id):
        # Asosiy bosh adminni (8907034180) bazadan o'chirib yubormaslik uchun himoya
        if int(user_id) == 8907034180:
            return False
        self.cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        self.connection.commit()
        return True

    def get_admins(self):
        self.cursor.execute("SELECT user_id, name FROM admins")
        return self.cursor.fetchall()

    def is_admin(self, user_id):
        self.cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None

    def add_channel(self, channel_id, channel_link, channel_name):
        self.cursor.execute("INSERT OR REPLACE INTO channels (channel_id, channel_link, channel_name) VALUES (?, ?, ?)", 
                            (channel_id, channel_link, channel_name))
        self.connection.commit()

    def remove_channel(self, channel_id):
        self.cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        self.connection.commit()

    def get_channels(self):
        self.cursor.execute("SELECT channel_id, channel_link, channel_name FROM channels")
        return self.cursor.fetchall()

    def get_sub_status(self):
        self.cursor.execute("SELECT value FROM settings WHERE key = 'sub_status'")
        res = self.cursor.fetchone()
        return res[0] if res else 'ON'

    def toggle_sub_status(self):
        current = self.get_sub_status()
        new_status = 'OFF' if current == 'ON' else 'ON'
        self.cursor.execute("UPDATE settings SET value = ? WHERE key = 'sub_status'", (new_status,))
        self.connection.commit()
        return new_status

    def add_movie(self, movie_id, title, description, duration, year):
        self.cursor.execute("INSERT INTO movies (movie_id, title, description, duration, year) VALUES (?, ?, ?, ?, ?)", 
                            (movie_id, title, description, duration, year))
        self.connection.commit()

    def add_movie_part(self, movie_id, part_number, file_id):
        self.cursor.execute("INSERT INTO movie_parts (movie_id, part_number, file_id) VALUES (?, ?, ?)", 
                            (movie_id, part_number, file_id))
        self.connection.commit()

    def get_movies(self):
        self.cursor.execute("SELECT movie_id, title, views, rating FROM movies")
        return self.cursor.fetchall()

    def get_movie_by_id(self, movie_id):
        self.cursor.execute("SELECT movie_id, title, description, duration, year, views, rating FROM movies WHERE movie_id = ?", (movie_id,))
        return self.cursor.fetchone()

    def search_movies_by_name(self, name):
        self.cursor.execute("SELECT movie_id, title, views, rating FROM movies WHERE title LIKE ?", (f"%{name}%",))
        return self.cursor.fetchall()

    def get_random_movie(self):
        self.cursor.execute("SELECT movie_id, title, views, rating FROM movies ORDER BY RANDOM() LIMIT 1")
        return self.cursor.fetchone()

    def get_movie_parts(self, movie_id):
        self.cursor.execute("SELECT part_id, part_number, file_id FROM movie_parts WHERE movie_id = ?", (movie_id,))
        return self.cursor.fetchall()

    def delete_movie(self, movie_id):
        self.cursor.execute("DELETE FROM movies WHERE movie_id = ?", (movie_id,))
        self.cursor.execute("DELETE FROM movie_parts WHERE movie_id = ?", (movie_id,))
        self.connection.commit()

    def increment_views(self, movie_id):
        self.cursor.execute("UPDATE movies SET views = views + 1 WHERE movie_id = ?", (movie_id,))
        self.connection.commit()

    def get_top_movies(self):
        self.cursor.execute("SELECT movie_id, title, views, rating FROM movies ORDER BY views DESC LIMIT 10")
        return self.cursor.fetchall()

    def add_favorite(self, user_id, movie_id):
        self.cursor.execute("INSERT OR IGNORE INTO favorites (user_id, movie_id) VALUES (?, ?)", (user_id, movie_id))
        self.connection.commit()

    def get_favorites(self, user_id):
        self.cursor.execute("""
            SELECT m.movie_id, m.title FROM movies m 
            JOIN favorites f ON m.movie_id = f.movie_id 
            WHERE f.user_id = ?
        """, (user_id,))
        return self.cursor.fetchall()

    def add_search_history(self, user_id, movie_id):
        self.cursor.execute("DELETE FROM search_history WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
        self.cursor.execute("INSERT INTO search_history (user_id, movie_id) VALUES (?, ?)", (user_id, movie_id))
        self.connection.commit()

    def get_search_history(self, user_id):
        self.cursor.execute("""
            SELECT m.movie_id, m.title FROM movies m 
            JOIN search_history h ON m.movie_id = h.movie_id 
            WHERE h.user_id = ? ORDER BY h.history_id DESC LIMIT 10
        """, (user_id,))
        return self.cursor.fetchall()

    def add_review(self, movie_id, user_id, rating, comment):
        self.cursor.execute("INSERT INTO reviews (movie_id, user_id, rating, comment) VALUES (?, ?, ?, ?)", 
                            (movie_id, user_id, rating, comment))
        self.connection.commit()
        self.cursor.execute("SELECT AVG(rating), COUNT(rating) FROM reviews WHERE movie_id = ?", (movie_id,))
        avg_r, count_r = self.cursor.fetchone()
        self.cursor.execute("UPDATE movies SET rating = ?, rating_count = ? WHERE movie_id = ?", (avg_r or 0.0, count_r or 0, movie_id))
        self.connection.commit()