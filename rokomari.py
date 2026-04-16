import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import re
import time

BASE_URL = "https://www.rokomari.com"
SEARCH_TERM = "islamic book"
MAX_PAGES = 5
OUTPUT_FILE = "rokomari_islamic_books.xlsx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    )
}


def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_url(href):
    full_url = urljoin(BASE_URL, href)
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def clean_price(price_text):
    if not price_text:
        return None

    text = str(price_text)
    text = text.replace("TK.", "").replace("Tk.", "").replace("TK", "").replace(",", "").strip()

    match = re.search(r"\d+(\.\d+)?", text)
    if match:
        return float(match.group())
    return None


def get_search_url(page_num):
    return f"{BASE_URL}/search?term=islamic+book&search_type=ALL&page={page_num}"


def extract_prices(price_block):
    if not price_block:
        return None, None

    old_price = None
    current_price = None

    old_el = price_block.select_one("strike.original-price")
    if old_el:
        old_price = clean_text(old_el.get_text(" ", strip=True))

    full_text = clean_text(price_block.get_text(" ", strip=True))
    all_prices = re.findall(r"TK\.?\s*[\d,]+", full_text, flags=re.I)

    if len(all_prices) == 1:
        if old_price:
            current_price = None
        else:
            current_price = all_prices[0]
    elif len(all_prices) >= 2:
        current_price = all_prices[-1]
        if not old_price:
            old_price = all_prices[0]

    return current_price, old_price


def extract_rating_review(card):
    text = clean_text(card.get_text(" ", strip=True))

    rating_count = None

    bracket_nums = re.findall(r"\((\d+)\)", text)
    if bracket_nums:
        rating_count = int(bracket_nums[0])
    return rating_count


def scrape_one_page(html, seen_urls, page_num):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.books-wrapper__item")

    print(f"Page {page_num}: items found = {len(cards)}")

    books = []

    for card in cards:
        try:
            link_el = card.select_one('a[href*="/book/"]')
            if not link_el:
                continue

            href = link_el.get("href")
            if not href:
                continue

            full_url = normalize_url(href)

            if full_url in seen_urls:
                continue

            title_el = card.select_one("h4.book-title")
            author_el = card.select_one("p.book-author")
            status_el = card.select_one("p.book-status")
            price_el = card.select_one("p.book-price")

            raw_title = clean_text(title_el.get_text(" ", strip=True)) if title_el else None
            raw_author = clean_text(author_el.get_text(" ", strip=True)) if author_el else None
            stock_text = clean_text(status_el.get_text(" ", strip=True)) if status_el else None

            raw_current_price, raw_original_price = extract_prices(price_el)
            ratings_count = extract_rating_review(card)

            if not raw_title or not raw_current_price:
                continue

            seen_urls.add(full_url)

            books.append({
                "raw_title": raw_title,
                "raw_author": raw_author,
                "raw_current_price": raw_current_price,
                "raw_original_price": raw_original_price,
                "ratings_count": ratings_count,
                "stock_text": stock_text,
                "url": full_url
            })

        except:
            continue

    return books


def prepare_data(products):
    raw_df = pd.DataFrame(products)

    if raw_df.empty:
        return raw_df, raw_df

    clean_df = raw_df.copy()

    clean_df["title"] = clean_df["raw_title"].apply(clean_text)
    clean_df["author"] = clean_df["raw_author"].apply(lambda x: clean_text(x) if pd.notna(x) else None)
    clean_df["current_price"] = clean_df["raw_current_price"].apply(lambda x: clean_text(x) if pd.notna(x) else None)
    clean_df["original_price"] = clean_df["raw_original_price"].apply(lambda x: clean_text(x) if pd.notna(x) else None)

    clean_df["current_price_num"] = clean_df["current_price"].apply(clean_price)

    clean_df["title_lower"] = clean_df["title"].str.lower()
    # clean_df["score"] = clean_df["ratings_count"] / clean_df["current_price_num"]
    
    clean_df = clean_df.drop(columns= ["raw_title", "raw_author", "raw_current_price", "raw_original_price"])

    clean_df = clean_df.drop_duplicates(subset=["url"])
    clean_df = clean_df.dropna(subset=["title", "current_price_num", "url"]).reset_index(drop=True)

    return raw_df, clean_df


def finalize_df(df):
    df = df.drop(columns=["title_lower", "current_price_num"], errors="ignore")

    preferred_end = ["ratings_count", "stock_text", "url"]

    existing_front = [col for col in df.columns if col not in preferred_end]
    existing_end = [col for col in preferred_end if col in df.columns]

    return df[existing_front + existing_end]


def make_clickable_links(writer, sheet_name, df, url_col_name="url"):
    ws = writer.sheets[sheet_name]

    if url_col_name not in df.columns:
        return

    col_idx = df.columns.get_loc(url_col_name) + 1

    for row_num, url in enumerate(df[url_col_name], start=2):
        cell = ws.cell(row=row_num, column=col_idx)
        cell.hyperlink = url
        cell.value = url
        cell.style = "Hyperlink"

    col_letter = ws.cell(row=1, column=col_idx).column_letter
    ws.column_dimensions[col_letter].width = 60


def save_all_outputs(products, filename):
    if not products:
        print("No books to save.")
        return

    raw_df, clean_df = prepare_data(products)

    if raw_df.empty or clean_df.empty:
        print("No valid cleaned books to save.")
        return

    priced_df = clean_df.dropna(subset=["current_price_num"]).copy()
    rated_df = clean_df.dropna(subset=["ratings_count"]).copy()

    cheapest_df = priced_df.sort_values("current_price_num", ascending=True)
    expensive_df = priced_df.sort_values("current_price_num", ascending=False)

    top_rated_df = rated_df.sort_values("ratings_count", ascending=False)

    under_200_df = priced_df[
        priced_df["current_price_num"] < 200
    ].sort_values("current_price_num", ascending=True)

    between_200_500_df = priced_df[
        (priced_df["current_price_num"] >= 200) & (priced_df["current_price_num"] <= 500)
    ].sort_values("current_price_num", ascending=True)

    above_500_df = priced_df[
        priced_df["current_price_num"] > 500
    ].sort_values("current_price_num", ascending=True)

    quran_df = clean_df[clean_df["title_lower"].str.contains(r"কুরআন|quran|qur'an", na=False, regex=True)]
    hadith_df = clean_df[clean_df["title_lower"].str.contains(r"হাদিস|hadith", na=False, regex=True)]

    top_cheapest_50_df = cheapest_df.head(50)
    best_books_df = clean_df[
        (clean_df["ratings_count"] >= 5) & 
        (clean_df["current_price_num"] > 0)
    ].copy()

    best_books_df["score"] = best_books_df["ratings_count"] / best_books_df["current_price_num"]

    best_books_df = best_books_df.sort_values("score", ascending=False)

    sheets = {
        "Raw": raw_df,
        "Clean": clean_df,
        "Cheapest": cheapest_df,
        "Most Expensive": expensive_df,
        "Top Rated": top_rated_df,
        "Under 200": under_200_df,
        "200 to 500": between_200_500_df,
        "Above 500": above_500_df,
        "Quran": quran_df,
        "Hadith": hadith_df,
        "Top Cheapest 50": top_cheapest_50_df,
        "Best Books Recommended" : best_books_df
    }

    sheets = {sheet_name: finalize_df(df) for sheet_name, df in sheets.items()}

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            make_clickable_links(writer, sheet_name, df, "url")

    print(f"Saved to {filename}")


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    all_books = []
    seen_urls = set()

    for page_num in range(1, MAX_PAGES + 1):
        url = get_search_url(page_num)
        print(f"Scraping page {page_num}: {url}")

        response = session.get(url, timeout=30)
        response.raise_for_status()

        books = scrape_one_page(response.text, seen_urls, page_num)

        if page_num == 1 and not books:
            print("No books found on page 1. Selectors may need a small update.")
            break

        all_books.extend(books)
        time.sleep(1)

    print(f"\nTotal unique books scraped: {len(all_books)}")
    save_all_outputs(all_books, OUTPUT_FILE)


if __name__ == "__main__":
    main()