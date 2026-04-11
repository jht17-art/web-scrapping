import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://quotes.toscrape.com/"
quotes_list = []
authors_list = []
# n = 5
while True:
    r = requests.get(url)
    soup = BeautifulSoup(r.text,"lxml")

    quotes = soup.find_all("span", {"class": "text"})
    for i in quotes:
        quote = i.text
        quotes_list.append(quote)
    # print(len(quotes_list))

    authors = soup.find_all("small", {"class": "author"})
    
    for i in authors:
        author = i.text
        authors_list.append(author)
    # print(authors_list)
    # print(len(authors_list))
    next_btn = soup.find("li", class_="next")
    if next_btn:
        next_link = next_btn.find("a")["href"]
        url = "https://quotes.toscrape.com" + next_link
        # n=n-1
    else:
        break

df = pd.DataFrame({"Quotes": quotes_list, "Authors": authors_list})
# print(df)
# df.to_csv("quotes.csv")
df.to_excel("quotes.xlsx", index=False)
