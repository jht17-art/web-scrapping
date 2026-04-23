from playwright.sync_api import sync_playwright
from urllib.parse import quote, urljoin, urlparse
import pandas as pd
import re

QUERY = "kawaii pen"
MAX_PAGES = 41

LISTING_FILE = "daraz_listing.xlsx"
FINAL_FILE = "daraz_full_dataset.xlsx"


# ---------------------------------
# Helpers
# ---------------------------------
def clean_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_url(href):
    full_url = urljoin("https://www.daraz.com.bd", href)
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def clean_price(price_text):
    if not price_text:
        return None
    text = str(price_text).replace("৳", "").replace(",", "").strip()
    m = re.search(r"\d+(\.\d+)?", text)
    return float(m.group()) if m else None


def clean_int(text):
    if not text:
        return None
    m = re.search(r"(\d[\d,]*)", str(text))
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def clean_float(text):
    if not text:
        return None
    m = re.search(r"(\d+(\.\d+)?)", str(text))
    if m:
        return float(m.group(1))
    return None


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


def finalize_df(df):
    preferred_end = [
        "rating_score",
        "rating_count",
        "answered_questions",
        "brand",
        "seller",
        "description",
        "url",
    ]
    front = [c for c in df.columns if c not in preferred_end]
    end = [c for c in preferred_end if c in df.columns]
    return df[front + end]


# ---------------------------------
# Stage 1: listing pages
# ---------------------------------
def scrape_listing_page(page, seen_urls, page_num):
    products = []

    cards = page.locator('div[data-qa-locator="product-item"]')
    total_cards = cards.count()
    print(f"Page {page_num}: products found = {total_cards}")

    for i in range(total_cards):
        try:
            card = cards.nth(i)

            title_link = card.locator('a[title]').first
            if title_link.count() == 0:
                continue

            href = title_link.get_attribute("href")
            name = title_link.get_attribute("title")

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
                "page": page_num,
                "name": clean_text(name),
                "price": price,
                "price_num": clean_price(price),
                "url": full_url
            })

        except:
            continue

    return products


def stage1_scrape_listing():
    all_products = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1400, "height": 900})

        # block heavy resources
        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "media", "font"]
            else route.continue_()
        )

        page = context.new_page()

        for page_num in range(1, MAX_PAGES + 1):
            search_url = f"https://www.daraz.com.bd/catalog/?page={page_num}&q={quote(QUERY)}"
            print(f"\nScraping listing page {page_num}: {search_url}")

            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            html = page.content()
            if "Captcha Interception" in html or "_____tmd_____/punish" in page.url:
                print("Captcha detected on listing page. Please solve it in browser.")
                page.wait_for_timeout(20000)

            products = scrape_listing_page(page, seen_urls, page_num)

            if not products:
                print("No products found on this listing page.")
                continue

            all_products.extend(products)

        browser.close()

    listing_df = pd.DataFrame(all_products)

    if not listing_df.empty:
        with pd.ExcelWriter(LISTING_FILE, engine="openpyxl") as writer:
            listing_df.to_excel(writer, sheet_name="Listing", index=False)
            make_clickable_links(writer, "Listing", listing_df, "url")

    print(f"\nTotal unique listing products: {len(all_products)}")
    print(f"Saved listing data to {LISTING_FILE}")

    return listing_df


# ---------------------------------
# Stage 2: detail pages
# ---------------------------------
def extract_first_text(page, selectors, timeout=2000):
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                text = loc.inner_text(timeout=timeout)
                text = clean_text(text)
                if text:
                    return text
        except:
            continue
    return None


def extract_all_texts(page, selector, timeout=2000):
    texts = []
    try:
        locs = page.locator(selector)
        count = locs.count()
        for i in range(count):
            try:
                txt = clean_text(locs.nth(i).inner_text(timeout=timeout))
                if txt:
                    texts.append(txt)
            except:
                pass
    except:
        pass
    return texts


def extract_detail_data(page, url, idx, total):
    print(f"Detail {idx}/{total}: {url}")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)

        html = page.content()
        if "Captcha Interception" in html or "_____tmd_____/punish" in page.url:
            print("Captcha detected on detail page. Please solve it in browser.")
            page.wait_for_timeout(20000)

        # rating score
        rating_score_text = extract_first_text(page, [
            "span.score-average",
            "div.score span.score-average",
        ])
        rating_score = clean_float(rating_score_text)

        # rating count and answered questions from the review summary links
        summary_links = extract_all_texts(page, "a.pdp-review-summary__link")

        rating_count = None
        answered_questions = None

        for txt in summary_links:
            low = txt.lower()
            if "rating" in low:
                rating_count = clean_int(txt)
            elif "answered question" in low:
                answered_questions = clean_int(txt)

        # fallback for rating count from count block like "0 Ratings"
        if rating_count is None:
            rating_count_text = extract_first_text(page, [
                "div.count",
                "div.mod-rating div.count",
            ])
            rating_count = clean_int(rating_count_text)

        # brand
        brand = extract_first_text(page, [
            "a.pdp-product-brand__brand-link",
            "div.pdp-product-brand a",
        ])

        # seller
        seller = extract_first_text(page, [
            "a.seller-name__detail-name",
            "div.seller-name__detail a",
        ])

        # description
        description = extract_first_text(page, [
            "div.html-content.detail-content",
            "div.html-content.detail-content article.lzd-article",
            "article.lzd-article",
        ], timeout=2500)

        return {
            "url": url,
            "rating_score": rating_score,
            "rating_count": rating_count,
            "answered_questions": answered_questions,
            "brand": brand,
            "seller": seller,
            "description": description,
        }

    except Exception as e:
        print(f"Failed detail page: {e}")
        return {
            "url": url,
            "rating_score": None,
            "rating_count": None,
            "answered_questions": None,
            "brand": None,
            "seller": None,
            "description": None,
        }


def stage2_scrape_details(listing_df):
    if listing_df.empty:
        print("Listing DataFrame is empty. Cannot scrape details.")
        return pd.DataFrame()

    urls = listing_df["url"].dropna().unique().tolist()
    detail_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1400, "height": 900})

        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "media", "font"]
            else route.continue_()
        )

        page = context.new_page()

        for idx, url in enumerate(urls, start=1):
            row = extract_detail_data(page, url, idx, len(urls))
            detail_rows.append(row)

            page.wait_for_timeout(1200)

        browser.close()

    detail_df = pd.DataFrame(detail_rows)
    print(f"Scraped detail pages: {len(detail_df)}")
    return detail_df


# ---------------------------------
# Stage 3: merge + outputs
# ---------------------------------
def prepare_final_data(listing_df, detail_df):
    if listing_df.empty:
        return pd.DataFrame()
    final_df = listing_df.merge(detail_df, on="url", how="left")

    final_df["price_num"] = final_df["price"].apply(clean_price)
    final_df["rating_score"] = pd.to_numeric(final_df["rating_score"], errors="coerce")
    final_df["rating_count"] = pd.to_numeric(final_df["rating_count"], errors="coerce")
    final_df["answered_questions"] = pd.to_numeric(final_df["answered_questions"], errors="coerce")

    # best value: strong rating score + more ratings + lower price
    scored_df = final_df.dropna(subset=["price_num", "rating_score"]).copy()
    scored_df = scored_df[scored_df["price_num"] > 0].copy()

    if not scored_df.empty:
        scored_df["rating_count_filled"] = scored_df["rating_count"].fillna(0)
        scored_df["value_score"] = (
            (scored_df["rating_score"] * (1 + scored_df["rating_count_filled"] / 100))
            / scored_df["price_num"]
        )
        final_df = final_df.merge(
            scored_df[["url", "value_score"]],
            on="url",
            how="left"
        )
    else:
        final_df["value_score"] = None

    return final_df


def save_final_outputs(final_df):
    if final_df.empty:
        print("No final data to save.")
        return

    priced_df = final_df.dropna(subset=["price_num"]).copy()
    rated_df = final_df.dropna(subset=["rating_score"]).copy()
    valued_df = final_df.dropna(subset=["value_score"]).copy()

    cheapest_df = priced_df.sort_values("price_num", ascending=True)
    top_rated_df = rated_df.sort_values(
        ["rating_score", "rating_count"],
        ascending=[False, False],
        na_position="last"
    )
    best_value_df = valued_df.sort_values("value_score", ascending=False)

    sheets = {
        "Combined": final_df,
        "Cheapest": cheapest_df,
        "Top Rated": top_rated_df,
        "Best Value": best_value_df,
    }

    sheets = {name: finalize_df(df) for name, df in sheets.items()}

    with pd.ExcelWriter(FINAL_FILE, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            make_clickable_links(writer, sheet_name, df, "url")

    print(f"Saved final output to {FINAL_FILE}")


# ---------------------------------
# Main
# ---------------------------------
def main():
    listing_df = stage1_scrape_listing()

    if listing_df.empty:
        print("Stage 1 failed or returned no products.")
        return

    detail_df = stage2_scrape_details(listing_df)

    final_df = prepare_final_data(listing_df, detail_df)
    save_final_outputs(final_df)


if __name__ == "__main__":
    main()