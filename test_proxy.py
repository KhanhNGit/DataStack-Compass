import requests
import urllib.parse
from bs4 import BeautifulSoup

url = "https://medium.com/kaggle-blog/recruit-ponpare-is-japans-leading-joint-coupon-site-offering-huge-discounts-on-everything-from-2295e397c7ea?source=rss----4b0982ce16a3---4"

proxies = [
    f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(url)}",
    f"https://corsproxy.io/?{urllib.parse.quote(url)}"
]

for p in proxies:
    try:
        print(f"Trying {p}")
        resp = requests.get(p, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        og_title = soup.find('meta', property='og:title')
        if og_title:
            print("FOUND:", og_title['content'])
            break
        elif soup.title:
            print("FOUND:", soup.title.string)
            break
    except Exception as e:
        print("FAILED:", e)
