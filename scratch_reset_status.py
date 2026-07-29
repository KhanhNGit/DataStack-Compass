import sqlite3

def reset_status():
    conn = sqlite3.connect('reports/blog/sql/blogs.db')
    c = conn.cursor()
    c.execute("UPDATE blogs SET status = 'RAW'")
    conn.commit()
    print("Database status reset to 'RAW'.")
    conn.close()

if __name__ == "__main__":
    reset_status()
