import requests
import pandas as pd
import time
from openpyxl import load_workbook

API_KEY = "AIzaSyDcQxKclLAMW5u8DXU5rpQnTwq22fxBlXg"

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL_BASE = "https://places.googleapis.com/v1/places/"

QUERIES = [
    "burger shops in Dhaka, Bangladesh",
    "burger restaurant in Dhaka, Bangladesh",
    "burger in Gulshan, Dhaka",
    "burger in Banani, Dhaka",
    "burger in Dhanmondi, Dhaka",
    "burger in Uttara, Dhaka"
]

SEARCH_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.priceLevel",
    "places.priceRange",
    "places.rating",
    "places.userRatingCount",
    "places.googleMapsUri",
    "nextPageToken",
])

DETAILS_FIELD_MASK = ",".join([
    "id",
    "displayName",
    "formattedAddress",
    "nationalPhoneNumber",
    "internationalPhoneNumber",
    "websiteUri",
    "googleMapsUri",
    "priceLevel",
    "priceRange",
    "rating",
    "userRatingCount",
])

PRICE_MAP = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4
}

PRICE_TEXT_MAP = {
    "PRICE_LEVEL_FREE": "Free",
    "PRICE_LEVEL_INEXPENSIVE": "Cheap",
    "PRICE_LEVEL_MODERATE": "Moderate",
    "PRICE_LEVEL_EXPENSIVE": "Expensive",
    "PRICE_LEVEL_VERY_EXPENSIVE": "Very Expensive"
}


def headers(field_mask: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": field_mask,
    }


def money_to_text(money_obj):
    if not money_obj:
        return None

    currency = money_obj.get("currencyCode", "")
    units = money_obj.get("units", "0")
    nanos = money_obj.get("nanos", 0)

    try:
        units = int(units)
    except Exception:
        units = 0

    try:
        nanos = int(nanos)
    except Exception:
        nanos = 0

    value = units + (nanos / 1_000_000_000)

    if currency:
        return f"{currency} {value:.2f}"
    return f"{value:.2f}"


def parse_price_range(price_range_obj):
    if not price_range_obj:
        return None, None

    start_price = money_to_text(price_range_obj.get("startPrice"))
    end_price = money_to_text(price_range_obj.get("endPrice"))
    return start_price, end_price


def fetch_text_search_page(query, page_token=None):
    body = {
        "textQuery": query,
        "pageSize": 20,
    }

    if page_token:
        body["pageToken"] = page_token

    response = requests.post(
        TEXT_SEARCH_URL,
        headers=headers(SEARCH_FIELD_MASK),
        json=body,
        timeout=30,
    )

    
    print("\nREQUEST BODY:", body)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    response.raise_for_status()
    return response.json()


def fetch_place_details(place_id: str):
    url = f"{DETAILS_URL_BASE}{place_id}"

    response = requests.get(
        url,
        headers=headers(DETAILS_FIELD_MASK),
        timeout=30,
    )

    if response.status_code != 200:
        print(f"Details failed for {place_id}: {response.status_code}")
        print(response.text)

    response.raise_for_status()
    return response.json()


def make_excel_links_clickable(filename, sheet_name):
    wb = load_workbook(filename)
    ws = wb[sheet_name]

    headers_map = {}
    for col in range(1, ws.max_column + 1):
        header_value = ws.cell(row=1, column=col).value
        headers_map[header_value] = col

    website_col = headers_map.get("Website")
    maps_col = headers_map.get("GoogleMapsLink")

    for row in range(2, ws.max_row + 1):
        if website_col:
            cell = ws.cell(row=row, column=website_col)
            if isinstance(cell.value, str) and cell.value.startswith(("http://", "https://")):
                cell.hyperlink = cell.value
                cell.style = "Hyperlink"

        if maps_col:
            cell = ws.cell(row=row, column=maps_col)
            if isinstance(cell.value, str) and cell.value.startswith(("http://", "https://")):
                cell.hyperlink = cell.value
                cell.style = "Hyperlink"

    wb.save(filename)


def collect_places():
    all_places = []
    seen_ids = set()

    for query in QUERIES:
        print(f"\nSearching: {query}")

        next_page_token = None
        page_count = 0
        max_pages = 5

        while page_count < max_pages:
            search_data = fetch_text_search_page(query, next_page_token)
            places = search_data.get("places", [])

            for place in places:
                place_id = place.get("id")
                if place_id and place_id not in seen_ids:
                    seen_ids.add(place_id)
                    place["_query"] = query
                    all_places.append(place)

            next_page_token = search_data.get("nextPageToken")
            page_count += 1

            if not next_page_token:
                break

            time.sleep(2)

    return all_places


def build_dataframes(all_places):
    raw_rows = []

    for idx, place in enumerate(all_places, start=1):
        place_id = place.get("id")
        if not place_id:
            continue

        name = place.get("displayName", {}).get("text")
        address = place.get("formattedAddress")
        rating = place.get("rating")
        rating_count = place.get("userRatingCount")
        maps_link = place.get("googleMapsUri")
        price_level = place.get("priceLevel")
        start_price, end_price = parse_price_range(place.get("priceRange"))
        query_used = place.get("_query")

        phone = None
        website = None

        try:
            detail = fetch_place_details(place_id)

            phone = detail.get("nationalPhoneNumber") or detail.get("internationalPhoneNumber")
            website = detail.get("websiteUri")

            if not name:
                name = detail.get("displayName", {}).get("text")
            if not address:
                address = detail.get("formattedAddress")
            if rating is None:
                rating = detail.get("rating")
            if rating_count is None:
                rating_count = detail.get("userRatingCount")
            if not maps_link:
                maps_link = detail.get("googleMapsUri")
            if not price_level:
                price_level = detail.get("priceLevel")
            if not start_price and not end_price:
                start_price, end_price = parse_price_range(detail.get("priceRange"))

        except Exception as e:
            print(f"[WARN] Details failed for {place_id}: {e}")

        raw_rows.append({
            "Name": name,
            "Address": address,
            "Phone": phone,
            "Rating": rating,
            "RatingCount": rating_count,
            "PriceLevel": PRICE_TEXT_MAP.get(price_level),
            "PriceRangeStart": start_price,
            "PriceRangeEnd": end_price,
            "GoogleMapsLink": maps_link,
            "Website": website,
            "PlaceID": place_id,
            "Query": query_used,
        })

        if idx % 10 == 0:
            print(f"Processed {idx}/{len(all_places)} places")

        time.sleep(0.2)

    df_raw = pd.DataFrame(raw_rows)

    # Cleaned copy
    df_clean = df_raw.copy()

    # Keep only Dhaka rows
    df_clean = df_clean[df_clean["Address"].str.contains("Dhaka", case=False, na=False)]

    # Remove duplicates
    df_clean = df_clean.drop_duplicates(subset=["PlaceID"])

    # Trim spaces only for text columns
    text_cols = ["Name", "Address", "Phone", "GoogleMapsLink", "Website", "Query", "PriceLevel", "PriceLevelText"]
    for col in text_cols:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # Convert missing values to blank Excel cells
    df_raw = df_raw.where(pd.notna(df_raw), pd.NA)
    df_clean = df_clean.where(pd.notna(df_clean), pd.NA)
    

    # Add numeric helper for sorting cheapest
    df_clean["PriceLevelNum"] = df_clean["PriceLevel"].map(PRICE_MAP)
    df_clean["ValueScore"] = df_clean["Rating"] / df_clean["PriceLevelNum"]
    # Top rated
    top_rated = df_clean.sort_values(
        by=["Rating", "RatingCount"],
        ascending=[False, False],
        na_position="last"
    ).head(10)

    # Cheapest / low price
    cheapest = df_clean[df_clean["PriceLevelNum"].notna()].sort_values(
        by=["PriceLevelNum", "Rating", "RatingCount"],
        ascending=[True, False, False],
        na_position="last"
    ).head(10)

    # Remove helper column from final exported views if you want
    export_clean = df_clean.drop(columns=["PriceLevelNum"])
    export_top = top_rated.drop(columns=["PriceLevelNum"], errors="ignore")
    export_cheapest = cheapest.drop(columns=["PriceLevelNum"], errors="ignore")

    return df_raw, export_clean, export_top, export_cheapest


def main():
    all_places = collect_places()
    print(f"\nTotal unique places collected: {len(all_places)}")

    df_raw, df_clean, df_top, df_cheapest = build_dataframes(all_places)

    output_file = "dhaka_burger_shops_mod.xlsx"

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_raw.to_excel(writer, sheet_name="Raw_Uncleaned_Data", index=False)
        df_clean.to_excel(writer, sheet_name="Cleaned_Data", index=False)
        df_top.to_excel(writer, sheet_name="Top_Rated", index=False)
        df_cheapest.to_excel(writer, sheet_name="Cheapest_LowPrice", index=False)

    for sheet in ["Raw_Uncleaned_Data", "Cleaned_Data", "Top_Rated", "Cheapest_LowPrice"]:
        make_excel_links_clickable(output_file, sheet)

    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()