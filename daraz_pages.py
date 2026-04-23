from playwright.sync_api import sync_playwright
from urllib.parse import quote, urljoin, urlparse
import pandas as pd
import re
import os

QUERY = "kawaii pen"
MAX_PAGES = 41

LISTING_FILE = "listing_resume.xlsx"
DETAIL_FILE = "detail_resume.xlsx"
FINAL_FILE = "final_dataset.xlsx"

TABS = 4
DETAIL_SAVE_EVERY = 20


# -----------------------------
# Helpers
# -----------------------------
def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_url(href):
    full_url = urljoin("https://www.daraz.com.bd", href)
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def clean_price(text):
    if not text:
        return None
    text = str(text).replace("৳", "").replace(",", "")
    m = re.search(r"\d+(\.\d+)?", text)
    return float(m.group()) if m else None


def clean_int(text):
    if not text:
        return None
    m = re.search(r"(\d[\d,]*)", str(text))
    return int(m.group(1).replace(",", "")) if m else None


def clean_float(text):
    if not text:
        return None
    m = re.search(r"(\d+(\.\d+)?)", str(text))
    return float(m.group()) if m else None


def load_excel(file):
    return pd.read_excel(file) if os.path.exists(file) else pd.DataFrame()


def save_excel(df, file):
    if not df.empty:
        df.to_excel(file, index=False)


# -----------------------------
# Scrape listing page
# -----------------------------
def scrape_listing_page(page, page_num):
    url = f"https://www.daraz.com.bd/catalog/?page={page_num}&q={quote(QUERY)}"
    print(f"Listing {page_num}")

    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    cards = page.locator('div[data-qa-locator="product-item"]')
    rows = []

    for i in range(cards.count()):
        try:
            card = cards.nth(i)

            link = card.locator('a[title]').first
            if link.count() == 0:
                continue

            href = link.get_attribute("href")
            name = link.get_attribute("title")

            price_el = card.locator("span.ooOxS").first
            if price_el.count() == 0:
                continue

            price = clean_text(price_el.inner_text())

            rows.append({
                "name": clean_text(name),
                "price": price,
                "price_num": clean_price(price),
                "url": normalize_url(href)
            })

        except:
            continue

    return rows


# -----------------------------
# Stage 1 (SAFE PARALLEL)
# -----------------------------
def stage1():
    existing = load_excel(LISTING_FILE)
    done_pages = set(existing["page"]) if not existing.empty else set()

    remaining = [p for p in range(1, MAX_PAGES+1) if p not in done_pages]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "font", "media"]
            else route.continue_()
        )

        pages = [context.new_page() for _ in range(TABS)]
        all_rows = []

        while remaining:
            batch = remaining[:TABS]
            remaining = remaining[TABS:]

            for i, page_num in enumerate(batch):
                pages[i].goto(
                    f"https://www.daraz.com.bd/catalog/?page={page_num}&q={quote(QUERY)}",
                    wait_until="domcontentloaded"
                )

            for i, page_num in enumerate(batch):
                rows = scrape_listing_page(pages[i], page_num)
                all_rows.extend(rows)

        browser.close()

    df = pd.concat([existing, pd.DataFrame(all_rows)], ignore_index=True)
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)

    save_excel(df, LISTING_FILE)
    return df


# -----------------------------
# Scrape detail page
# -----------------------------
def scrape_detail(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        rating = clean_float(page.locator("span.score-average").first.inner_text())
        texts = page.locator("a.pdp-review-summary__link").all_inner_texts()

        rating_count = None
        questions = None

        for t in texts:
            if "Rating" in t:
                rating_count = clean_int(t)
            if "Answered" in t:
                questions = clean_int(t)

        brand = clean_text(page.locator("a.pdp-product-brand__brand-link").first.inner_text())
        seller = clean_text(page.locator("a.seller-name__detail-name").first.inner_text())
        desc = clean_text(page.locator("div.html-content.detail-content").first.inner_text())

        return {
            "url": url,
            "rating": rating,
            "rating_count": rating_count,
            "questions": questions,
            "brand": brand,
            "seller": seller,
            "description": desc
        }

    except:
        return {"url": url}


# -----------------------------
# Stage 2 (RESUME + BATCH SAVE)
# -----------------------------
def stage2(listing_df):
    existing = load_excel(DETAIL_FILE)
    done_urls = set(existing["url"]) if not existing.empty else set()

    urls = [u for u in listing_df["url"] if u not in done_urls]

    collected = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "font", "media"]
            else route.continue_()
        )

        pages = [context.new_page() for _ in range(TABS)]

        idx = 0
        while idx < len(urls):
            batch = urls[idx: idx + TABS]

            for i, url in enumerate(batch):
                pages[i].goto(url, wait_until="domcontentloaded")

            for i, url in enumerate(batch):
                row = scrape_detail(pages[i], url)
                collected.append(row)

            if len(collected) % DETAIL_SAVE_EVERY == 0:
                df = pd.concat([existing, pd.DataFrame(collected)])
                df = df.drop_duplicates("url")
                save_excel(df, DETAIL_FILE)
                collected.clear()
                print("Saved batch")

            idx += TABS

        browser.close()

    final_df = pd.concat([existing, pd.DataFrame(collected)])
    final_df = final_df.drop_duplicates("url")
    save_excel(final_df, DETAIL_FILE)

    return final_df


# -----------------------------
# Stage 3 (FINAL DATASET)
# -----------------------------
def make_clickable(ws, df):
    if "url" not in df.columns:
        return

    col_idx = df.columns.get_loc("url") + 1

    for i, url in enumerate(df["url"], start=2):
        cell = ws.cell(row=i, column=col_idx)
        cell.hyperlink = url
        cell.value = url
        cell.style = "Hyperlink"

    ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 60


def reorder_columns(df):
    end_cols = ["rating", "rating_count", "questions", "brand", "seller", "description", "url"]
    front = [c for c in df.columns if c not in end_cols]
    end = [c for c in end_cols if c in df.columns]
    return df[front + end]


def stage3(listing, detail):
    df = listing.merge(detail, on="url", how="left")

    # numeric cleanup
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce")

    # -------------------------
    # VALUE SCORE
    # -------------------------
    df["value_score"] = (
        (df["rating"] * (1 + df["rating_count"].fillna(0)/100))
        / df["price_num"]
    )

    # -------------------------
    # FILTERED DATAFRAMES
    # -------------------------
    priced_df = df.dropna(subset=["price_num"])
    rated_df = df.dropna(subset=["rating"])

    cheapest_df = priced_df.sort_values("price_num", ascending=True)
    top_rated_df = rated_df.sort_values(
        ["rating", "rating_count"],
        ascending=[False, False]
    )

    best_value_df = df.dropna(subset=["value_score"]).sort_values(
        "value_score", ascending=False
    )

    # -------------------------
    # COLUMN ORDER
    # -------------------------
    df = reorder_columns(df)
    cheapest_df = reorder_columns(cheapest_df)
    top_rated_df = reorder_columns(top_rated_df)
    best_value_df = reorder_columns(best_value_df)

    # -------------------------
    # SAVE MULTI-SHEET EXCEL
    # -------------------------
    with pd.ExcelWriter(FINAL_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Combined", index=False)
        cheapest_df.to_excel(writer, sheet_name="Cheapest", index=False)
        top_rated_df.to_excel(writer, sheet_name="Top Rated", index=False)
        best_value_df.to_excel(writer, sheet_name="Best Value", index=False)

        make_clickable(writer.sheets["Combined"], df)
        make_clickable(writer.sheets["Cheapest"], cheapest_df)
        make_clickable(writer.sheets["Top Rated"], top_rated_df)
        make_clickable(writer.sheets["Best Value"], best_value_df)

    print("✅ Final Excel with multiple sheets saved")

# -----------------------------
# MAIN
# -----------------------------
def main():
    listing = stage1()
    detail = stage2(listing)
    stage3(listing, detail)


if __name__ == "__main__":
    main()