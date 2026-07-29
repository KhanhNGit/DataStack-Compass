import sqlite3
conn = sqlite3.connect('reports/blog/sql/blogs.db')
c = conn.cursor()
c.execute("UPDATE blogs SET status = 'RAW', title = 'Recruit Ponpare is Japan’s leading joint coupon site, offering huge discounts on everything from…' WHERE url LIKE '%2295e397c7ea%'")
conn.commit()
conn.close()
print("Updated specific post to RAW with truncated title.")
