import requests
from bs4 import BeautifulSoup
import pandas as pd

data = []
team_name = input("Enter team name: ")

for page in range(1,25):
    url = f"https://www.scrapethissite.com/pages/forms/?page_num={page}&q={team_name}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text,"lxml")
    rows = soup.find_all("tr", {"class": "team"})
    if not rows:
        break
    for row in rows:
        name = row.find("td", {"class": "name"}).text.strip()
        year = int(row.find("td", {"class": "year"}).text.strip())
        wins = int(row.find("td", {"class": "wins"}).text.strip())
        losses = int(row.find("td", {"class": "losses"}).text.strip())
        ot_losses = int(row.find("td", {"class": "ot-losses"}).text.strip() or 0)
        pct_win = float(row.find("td", {"class": "pct"}).text.strip() or 0)
        gf = int(row.find("td", {"class": "gf"}).text.strip())
        ga = int(row.find("td", {"class": "ga"}).text.strip())
        diff = int(row.find("td", {"class": "diff"}).text.strip())
        data.append({
            "Team Name": name,
            "Year": year,
            "Wins": wins,
            "Losses": losses,
            "OT Losses": ot_losses,
            "Win %": pct_win,
            "Goals For": gf,
            "Goals Against": ga,
            "+/-": diff
        })
  

df = pd.DataFrame(data)
df.to_excel("hockey_search.xlsx", index=False)
