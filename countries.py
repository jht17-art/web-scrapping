import requests
from bs4 import BeautifulSoup
import pandas as pd


url = "https://www.scrapethissite.com/pages/simple/"

r = requests.get(url)
soup = BeautifulSoup(r.text,"lxml")

names_list = []
capitals_list = []
areas_list = []
population_list = []

names = soup.find_all("h3", {"class": "country-name"})
for i in names:
    name = i.text.strip().replace('"', "")
    names_list.append(name)
  
capitals = soup.find_all("span", {"class": "country-capital"})
for i in capitals:
    capital = i.text
    capitals_list.append(capital)
    
areas = soup.find_all("span", {"class": "country-area"})

for i in areas:
    area = float(i.text)
    areas_list.append(area)

population = soup.find_all("span", {"class": "country-population"})

for i in population:
    p = float(i.text)
    population_list.append(p)

df = pd.DataFrame({"Names": names_list, "Capitals": capitals_list, "Population": population_list, "Area(km\u00b2)": areas_list})
df.to_excel("countries.xlsx", index=False)
