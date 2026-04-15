from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import csv
import re
import pandas as pd

URL = "https://pages.daraz.com.bd/wow/gcp/route/daraz/bd/upr/router?hybrid=1&data_prefetch=true&prefetch_replace=1&at_iframe=1&wh_pid=%2Flazada%2Fmegascenario%2Fbd%2Fbrand-campaigns-april2026%2FUnileverSuperBrandDay&spm=a2a0e.tm80335411.bannerSliderDesktop.d_1"

# OUTPUT_FILE = "daraz_just_for_you.csv"

def save_to_excel(products, filename):
    df = pd.DataFrame(products)
    df.to_excel(filename, index=False)
    
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def scrape_products(page):
    cards = page.locator("a.jfy-product-card-component-pc")
    count = cards.count()
    print("Total cards found in DOM:", count)

    products = []
    seen_urls = set()

    for i in range(count):
        card = cards.nth(i)

        try:
            href = card.get_attribute("href")
        except:
            href = None

        if not href:
            continue

        full_url = urljoin("https://www.daraz.com.bd", href)

        # remove duplicates
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        try:
            name = card.locator(".product-card-title").inner_text(timeout=2000)
            name = clean_text(name)
        except:
            name = None

        current_price = None
        if card.locator(".lzdPriceDiscountPCV2").count() > 0:
            try:
                current_price = card.locator(".lzdPriceDiscountPCV2").inner_text(timeout=2000)
                current_price = clean_text(current_price)
            except:
                current_price = None

        old_price = None
        if card.locator(".lzdPriceOriginPCV2").count() > 0:
            try:
                old_price = card.locator(".lzdPriceOriginPCV2").inner_text(timeout=2000)
                old_price = clean_text(old_price)
            except:
                old_price = None

        # if product has no discount
        if not current_price and old_price:
            current_price = old_price
            old_price = None

        if name and current_price:
            products.append({
                "name": name,
                "current_price": current_price,
                "old_price": old_price,
                "url": full_url
            })

    return products


def save_to_csv(products, filename):
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "current_price", "old_price", "url"]
        )
        writer.writeheader()
        writer.writerows(products)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # fixed scrolling only 3 times
        for _ in range(3):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(2000)

        products = scrape_products(page)

        browser.close()

    print("Unique products:", len(products))
    for item in products[:10]:
        print(item)

    # save_to_csv(products, OUTPUT_FILE)
    # print("Saved to", OUTPUT_FILE)
    save_to_excel(products, "daraz_products.xlsx")


if __name__ == "__main__":
    main()