import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="test",
    user="postgres",
    password="test"
)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(50) NOT NULL
)
""")

cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
            ('testuser', '1234'))

conn.commit()
cur.close()
conn.close()

print("Table created and sample user added.")
