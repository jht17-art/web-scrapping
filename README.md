# 🕸️ Web Scraping & Data Analysis Projects

This repository contains multiple web scraping projects built using Python.  
The focus is not only on extracting data but also on cleaning, structuring, and analyzing it for real-world use.

---

## 📌 Projects Included

### 🛒 1. Daraz Product Scraper (Main Project)
- Scraped **1000+ products** using a **2-stage pipeline**
  - Listing pages → name, price, URL
  - Detail pages → rating, brand, seller, description
- Implemented:
  - Parallel tab-based scraping (performance optimization)
  - Error handling (timeouts, broken pages)
  - Resume support
- Created:
  - Clean dataset
  - Multi-sheet Excel output:
    - Combined
    - Cheapest
    - Top Rated
    - Best Value
- Added a custom metric to estimate **value for money**

📂 Files:
- `daraz_search.py`
- `daraz_kawaii_pen.xlsx`

---

### 📚 2. Rokomari Book Scraper
- Scraped Islamic books from Rokomari
- Extracted:
  - Title, author, price, rating
- Cleaned and structured data for analysis

📂 Files:
- `rokomari.py`
- `rokomari_islamic_books.xlsx`

---

### 🍔 3. Google Places API (Lead Generation)
- Collected business data (e.g., burger shops in Dhaka)
- Extracted:
  - Name, address, rating, website
- Structured for **lead generation use cases**

📂 Files:
- `google_api.py`
- `dhaka_burger_shops_final.xlsx`

---

### 📊 4. Practice Scraping Projects
Used to learn and practice scraping techniques:

- Quotes scraping (pagination, login handling)
- Books scraping (BeautifulSoup basics)
- Hockey dataset (table extraction)
- Yellow Pages (business listings)

📂 Files:
- `quotes.py`, `books.py`, `hockey.py`, `yellow_page.py`

---

## ⚙️ Tech Stack

- Python
- Playwright
- BeautifulSoup
- Pandas
- Regex
- OpenPyXL

---

## 🚀 Key Skills Demonstrated

- Multi-stage scraping pipelines  
- Handling dynamic websites (JS-heavy pages)  
- Performance optimization (parallel tabs)  
- Error handling & robustness  
- Data cleaning and transformation  
- Basic data analysis & feature engineering  

---

## 📈 Future Improvements

- Async scraping for further speed improvements  
- Dashboard/visualization layer  
- More advanced filtering and analytics  
- Deployment as a small data service  

---

## 🙌 Final Note

This repository reflects my journey from basic scraping to building more structured and optimized data pipelines.
