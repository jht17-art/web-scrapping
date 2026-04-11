from playwright.sync_api import sync_playwright
import pandas as pd


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    quotes_list=[]
    authors_list=[]
    
    page.goto("https://quotes.toscrape.com/js/")
    while True:
        page.wait_for_selector("div.quote")

        quotes = page.locator("div.quote")
        count = quotes.count()
        for i in range(count):
            text = quotes.nth(i).locator("span.text").inner_text()
            quotes_list.append(text)
            author = quotes.nth(i).locator("small.author").inner_text()
            authors_list.append(author)
        
        next_btn = page.locator("li.next a")

        if next_btn.count() > 0:
            next_btn.click()
            page.wait_for_selector("div.quote")  # wait for next page
        else:
            break

        # browser.close()
    df = pd.DataFrame({"Quotes": quotes_list, "Authors": authors_list})
    # print(df)
    # df.to_csv("quotes.csv")
    df.to_excel("quotes_play.xlsx", index=False)
    browser.close()