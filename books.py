import requests
from bs4 import BeautifulSoup
import pandas as pd

books_list = []
prices_list = []
rating_map = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5
}
ratings_list = []

for i in range(1,51):
    url = "https://books.toscrape.com/catalogue/page-"+str(i)+".html"

    r = requests.get(url)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text,"lxml")

    books = soup.find_all("article", {"class": "product_pod"})
    for i in books:
        book = i.find("h3").find("a")["title"]
        books_list.append(book)
  
    prices = soup.find_all("p", {"class": "price_color"})
    for i in prices:
        price = i.text.strip()
        prices_list.append(price)
    
    ratings = soup.find_all("p", class_="star-rating")

    for r in ratings:
        rating = r.get("class")[1]
        rating_num = rating_map[rating]
        ratings_list.append(rating_num)


df = pd.DataFrame({"Book Titles": books_list, "Prices": prices_list, "Ratings": ratings_list})
df.to_excel("books.xlsx", index=False)
