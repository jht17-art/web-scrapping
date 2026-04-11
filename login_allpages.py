import requests
import pandas as pd
from bs4 import BeautifulSoup

login_url = "https://quotes.toscrape.com/login"
base_url = "https://quotes.toscrape.com"

session = requests.Session()

# Get login page
response = session.get(login_url)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
csrf_token = soup.find("input", {"name": "csrf_token"})["value"]

# Login
payload = {
    "csrf_token": csrf_token,
    "username": "testuser",
    "password": "testpass"
}

login_response = session.post(login_url, data=payload)
login_response.raise_for_status()

if "Logout" in login_response.text:
    print("Login successful")
else:
    print("Login failed")

data = []
url = base_url

while True:
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    quotes = soup.find_all("div", class_="quote")

    for quote in quotes:
        text = quote.find("span", class_="text").get_text(strip=True)
        author = quote.find("small", class_="author").get_text(strip=True)
        tags = ", ".join(tag.get_text(strip=True) for tag in quote.find_all("a", class_="tag"))

        data.append({
            "Quote": text,
            "Author": author,
            "Tags": tags
        })

    next_btn = soup.find("li", class_="next")
    if next_btn:
        next_link = next_btn.find("a")["href"]
        url = base_url + next_link
    else:
        break

df = pd.DataFrame(data)
df.to_excel("all_quotes.xlsx", index=False)

print("Saved all quotes to all_quotes.xlsx")
print(df.head())