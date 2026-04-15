import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0"
}

data = []

other_cities = [
    "barisal", "chittagong", "khulna", "mymensingh",
    "rajshahi", "rangpur", "sylhet"
]

def is_valid_dhaka(address):
    if not address:
        return False
    
    addr = address.lower()
  
    if "dhaka" not in addr:
        return False
   
    for city in other_cities:
        if city in addr:
            return False
    
    return True

def extract_phone(card):
    phone_no = None
    
    for block in card.select("div.s"):
        if block.select_one("i.fa-phone"):
            span = block.find("span")
            if span:
                phone_no = span.get_text(strip=True)
                break
    
    return phone_no

for i in range(1, 55):
    if i == 1:
        url = "https://www.bangladeshyp.com/category/Restaurants/city:Dhaka"
        category = "Restaurant"
    elif 1 < i < 22:
        url = f"https://www.bangladeshyp.com/category/Restaurants/{i}/city:Dhaka"
        category = "Restaurant"
    elif i == 22:
        url = "https://www.bangladeshyp.com/category/Vehicle_services/city:Dhaka"
        category = "Vehicle services"
    else:
        url = f"https://www.bangladeshyp.com/category/Vehicle_services/{i-21}/city:Dhaka"
        category = "Vehicle services"

    print("Scraping:", url)
    print("Data: ")
    
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "lxml")

    companies = soup.select("div.company")
    print("Cards found:", len(companies))

    for company in companies:
        name = None
        address = None
        phone = None
        name_tag = company.find("h3")
        if name_tag and name_tag.find("a"):
            name = name_tag.find("a").get_text(strip=True)
           

        address_tag = company.find("div", class_="address")
        if address_tag:
            address = address_tag.get_text(" ", strip=True)
  
        phone_no = extract_phone(company)
      

        if name and address and is_valid_dhaka(address):
            data.append({
                "Name": name,
                "Address": address,
                "Phone": phone_no,
                "Category": category
            })

    time.sleep(1)

df = pd.DataFrame(data)

df = df.drop_duplicates(subset=["Name", "Address", "Phone", "Category"])

df.to_excel("byp.xlsx", index=False)
print(df.head())
print("Total rows:", len(df))