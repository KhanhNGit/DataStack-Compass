import sqlite3

conn = sqlite3.connect('reports/blog/sql/blogs.db')
c = conn.cursor()
c.execute("SELECT title, raw_content FROM blogs WHERE url LIKE '%2295e397c7ea%'")
row = c.fetchone()
if row:
    print(f"TITLE: {row[0]}")
    print(f"RAW_CONTENT: {row[1]}")
else:
    print("Not found")
conn.close()
