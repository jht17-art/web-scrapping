import requests
import pandas as pd
from bs4 import BeautifulSoup

login_url = "https://quotes.toscrape.com/login"
start_url = "https://quotes.toscrape.com/"

# Create session
session = requests.Session()

# Step 1: Get login page
response = session.get(login_url)
response.raise_for_status()

# Step 2: Extract CSRF token
soup = BeautifulSoup(response.text, "html.parser")
csrf_token = soup.find("input", {"name": "csrf_token"})["value"]

# Step 3: Login
payload = {
    "csrf_token": csrf_token,
    "username": "testuser",
    "password": "testpass"
}

login_response = session.post(login_url, data=payload)
login_response.raise_for_status()

# Step 4: Check login success
if "Logout" in login_response.text:
    print("Login successful")
else:
    print("Login failed")

# Step 5: Scrape quotes from first page
response = session.get(start_url)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
quote_blocks = soup.find_all("div", class_="quote")

data = []

for quote in quote_blocks:
    text = quote.find("span", class_="text").get_text(strip=True)
    author = quote.find("small", class_="author").get_text(strip=True)
    
    tag_elements = quote.find_all("a", class_="tag")
    tags = ", ".join(tag.get_text(strip=True) for tag in tag_elements)

    data.append({
        "Quote": text,
        "Author": author,
        "Tags": tags
    })

# Step 6: Convert to DataFrame
df = pd.DataFrame(data)

# Step 7: Save to Excel
df.to_excel("login.xlsx", index=False)

print("Data saved to quotes.xlsx")
print(df)