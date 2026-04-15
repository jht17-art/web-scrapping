from playwright.sync_api import sync_playwright
from urllib.parse import quote, urljoin, urlparse
import pandas as pd
import re

QUERY = "kawaii pen"
MAX_PAGES = 41
OUTPUT_FILE = "daraz_kawaii_pen.xlsx"


def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_url(href):
    full_url = urljoin("https://www.daraz.com.bd", href)
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def clean_price(price_text):
    if not price_text:
        return None

    price_text = str(price_text).replace("৳", "").replace(",", "").strip()

    try:
        return float(price_text)
    except:
        return None


def scrape_one_page(page, seen_urls, page_num):
    products = []

    cards = page.locator('div[data-qa-locator="product-item"]')
    count = cards.count()
    print(f"Page {page_num}: products found = {count}")

    for i in range(count):
        try:
            card = cards.nth(i)

            title_link = card.locator('a[title]').first
            if title_link.count() == 0:
                continue

            name = title_link.get_attribute("title")
            href = title_link.get_attribute("href")

            price_el = card.locator("span.ooOxS").first
            if price_el.count() == 0:
                continue

            price = clean_text(price_el.inner_text(timeout=2000))

            if not href or not name or not price:
                continue

            full_url = normalize_url(href)

            if full_url in seen_urls:
                continue

            seen_urls.add(full_url)

            products.append({
                "raw_name": name,
                "raw_price": price,
                "url": full_url
            })

        except:
            continue

    return products


def prepare_data(products):
    raw_df = pd.DataFrame(products)

    if raw_df.empty:
        return raw_df, raw_df

    clean_df = raw_df.copy()
    clean_df["name"] = clean_df["raw_name"].apply(clean_text)
    clean_df["price"] = clean_df["raw_price"].apply(clean_text)
    clean_df["price_num"] = clean_df["price"].apply(clean_price)
    clean_df["name_lower"] = clean_df["name"].str.lower()
    clean_df = clean_df.drop(columns=["raw_name", "raw_price"])

    clean_df = clean_df.drop_duplicates(subset=["url"])
    clean_df = clean_df.dropna(subset=["name", "price_num", "url"])


    return raw_df, clean_df


def make_clickable_links(writer, sheet_name, df, url_col_name):
    ws = writer.sheets[sheet_name]

    if url_col_name not in df.columns:
        return

    url_col_index = df.columns.get_loc(url_col_name) + 1

    for row_num, url in enumerate(df[url_col_name], start=2):
        cell = ws.cell(row=row_num, column=url_col_index)
        cell.hyperlink = url
        cell.value = url
        cell.style = "Hyperlink"

    # optional: widen URL column
    col_letter = ws.cell(row=1, column=url_col_index).column_letter
    ws.column_dimensions[col_letter].width = 60

def finalize_df(df):
    df = df.drop(columns=["name_lower"], errors="ignore")
    if "url" in df.columns:
        cols = [col for col in df.columns if col != "url"] + ["url"]
        df = df[cols]
    return df

def save_all_outputs(products, filename):
    if not products:
        print("No products to save.")
        return

    raw_df, clean_df = prepare_data(products)

    if raw_df.empty or clean_df.empty:
        print("No valid cleaned products to save.")
        return

    cheapest_df = clean_df.sort_values(by="price_num", ascending=True)
    expensive_df = clean_df.sort_values(by="price_num", ascending=False)

    under_100_df = clean_df[clean_df["price_num"] < 100]
    between_100_300_df = clean_df[(clean_df["price_num"] >= 100) & (clean_df["price_num"] <= 300)]
    above_300_df = clean_df[clean_df["price_num"] > 300]

    gel_pen_df = clean_df[clean_df["name_lower"].str.contains("gel pen", na=False)]
    ball_pen_df = clean_df[clean_df["name_lower"].str.contains("ball pen", na=False)]
    kawaii_df = clean_df[clean_df["name_lower"].str.contains("kawaii", na=False)]
    sanrio_df = clean_df[clean_df["name_lower"].str.contains("sanrio", na=False)]

    top_cheapest_50_df = cheapest_df.head(50)

    sheets = {
        "Raw": raw_df,
        "Clean": clean_df,
        "Cheapest": cheapest_df,
        "Most Expensive": expensive_df,
        "Under 100": under_100_df,
        "100 to 300": between_100_300_df,
        "Above 300": above_300_df,
        "Gel Pen": gel_pen_df,
        "Ball Pen": ball_pen_df,
        "Kawaii": kawaii_df,
        "Sanrio": sanrio_df,
        "Top Cheapest 50": top_cheapest_50_df,
    }

    sheets = {sheet_name: finalize_df(df) for sheet_name, df in sheets.items()}

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            make_clickable_links(writer, sheet_name, df, "url")
    print(f"Saved to {filename}")


def main():
    all_products = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        for page_num in range(1, MAX_PAGES + 1):
            search_url = f"https://www.daraz.com.bd/catalog/?page={page_num}&q={quote(QUERY)}"
            print(f"\nScraping page {page_num}: {search_url}")

            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            html = page.content()
            if "Captcha Interception" in html or "_____tmd_____/punish" in page.url:
                print("Captcha detected. Please solve it in the opened browser window.")
                page.wait_for_timeout(20000)

            products = scrape_one_page(page, seen_urls, page_num)

            if not products:
                print("No products found on this page.")
                continue

            all_products.extend(products)

        browser.close()

    print(f"\nTotal unique products scraped: {len(all_products)}")
    save_all_outputs(all_products, OUTPUT_FILE)


if __name__ == "__main__":
    main()