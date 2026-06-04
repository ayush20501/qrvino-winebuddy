import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.config import create_database_connection

BASE = "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

VIEWPORT = {"width": 1440, "height": 900}


def slugify(text):
    import re
    text = str(text).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\-]+", "", text)
    text = re.sub(r"\-\-+", "-", text)
    return text.strip("-")


def db_samples():
    conn = create_database_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    slug = None
    vrtl_key = None
    cstmr_key = None
    try:
        cur.execute(
            "SELECT AI_CSTMR_START_TXT, AI_CSTMR_KEY FROM ai_cstmr WHERE ACTV_IND = 'Y' LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            slug = slugify(row["AI_CSTMR_START_TXT"])
            cstmr_key = row["AI_CSTMR_KEY"]
        cur.execute("SELECT VRTL_KEY FROM ai_vrtl LIMIT 1")
        v = cur.fetchone()
        if v:
            vrtl_key = v["VRTL_KEY"]
    finally:
        cur.close()
        conn.close()
    return slug, vrtl_key, cstmr_key


def capture(page, name, url, wait_ms=4000, extra_wait_selector=None):
    page.goto(url, wait_until="networkidle", timeout=60000)
    if extra_wait_selector:
        try:
            page.wait_for_selector(extra_wait_selector, timeout=15000)
        except Exception:
            pass
    time.sleep(wait_ms / 1000)
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"OK {path.name} <- {url}")
    return path


def main():
    slug, vrtl_key, cstmr_key = db_samples()
    screens = [
        ("01_home", f"{BASE}/"),
        ("02_explore_wine", f"{BASE}/explore-wine"),
        ("03_explore_beer", f"{BASE}/explore-beer"),
        (
            "04_wine_brands_flow",
            f"{BASE}/brands?selectedOption=1&incoming=Grilled%20salmon",
        ),
        (
            "05_beer_brands_flow",
            f"{BASE}/brands?selectedOption=5&incoming=BBQ%20ribs",
        ),
    ]
    if vrtl_key:
        screens.append(("06_store_selection", f"{BASE}/stores?key={vrtl_key}"))
        screens.append(
            ("07_store_selection_modal", f"{BASE}/stores?key={vrtl_key}&modal=1")
        )
    if cstmr_key:
        screens.append(
            ("08_wine_seller_selection", f"{BASE}/wines/selection?ai_cstmr_key={cstmr_key}")
        )
    if slug:
        screens.append(("09_customer_chat", f"{BASE}/customer/chat/{slug}"))
    screens.append(
        (
            "10_recommendations_text",
            f"{BASE}/recommendations?chatbot_input=steak&chatbot_radio=red%20wine",
        )
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )
        page = context.new_page()

        for name, url in screens:
            try:
                sel = "#content" if name == "01_home" else None
                if name.startswith("02") or name.startswith("03"):
                    sel = ".wb-page, body"
                extra_ms = 6000 if name == "01_home" else 3500
                if name == "10_recommendations_text":
                    extra_ms = 25000
                capture(page, name, url, wait_ms=extra_ms, extra_wait_selector=sel)
            except Exception as e:
                print(f"FAIL {name}: {e}")

        if slug:
            try:
                page.goto(f"{BASE}/customer/chat/{slug}", wait_until="networkidle", timeout=60000)
                page.wait_for_selector("#login_form", timeout=15000)
                time.sleep(2)
                page.fill("#user_input", "grilled ribeye steak")
                page.click('button[type="submit"]')
                page.wait_for_selector(".wb-recommendations", timeout=90000)
                time.sleep(2)
                path = OUT / "11_customer_recommendations_table.png"
                page.screenshot(path=str(path), full_page=True)
                print(f"OK {path.name}")
            except Exception as e:
                print(f"FAIL 11_customer_recommendations: {e}")

            if vrtl_key:
                try:
                    page.goto(f"{BASE}/customer/chat/{slug}", wait_until="networkidle")
                    time.sleep(1)
                    page.goto(
                        f"{BASE}/customer/stores?key={vrtl_key}&testflag=1",
                        wait_until="networkidle",
                        timeout=60000,
                    )
                    time.sleep(3)
                    path = OUT / "12_customer_store_selection.png"
                    page.screenshot(path=str(path), full_page=True)
                    print(f"OK {path.name}")
                except Exception as e:
                    print(f"FAIL 12_customer_store_selection: {e}")

        browser.close()

    print(f"\nScreenshots saved to: {OUT}")


if __name__ == "__main__":
    main()
