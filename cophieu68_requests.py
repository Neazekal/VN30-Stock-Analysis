"""
Test: Thay the Selenium bang requests + BeautifulSoup de cao shares outstanding tu cophieu68.vn

Muc tieu:
- Test xem co cao duoc HTML tinh (server-rendered) khong can browser
- So sanh toc do voi phien ban Selenium
- Neu thanh cong, the co the thay the hoan toan cophieu68_selenium.py

Cach hoat dong:
- Truy cap truc tiep URL: https://www.cophieu68.vn/quote/event_calc_volume.php?id=<symbol>
- Parse HTML voi BeautifulSoup, trich bang co chua "Ngay bo sung"
- Luu CSV giong format cu

Su khac biet voi Selenium:
- KHONG can Chrome / ChromeDriver
- KHONG co ad popup, KHONG can click qua flow
- 1-2s / ma thay vi 30-60s / ma
- Chi hoat dong neu trang khong can JS de render (se biet sau khi test)
"""

import csv
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# VN30 (danh sach hien hanh)
VN30_STOCKS = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
]
# VN30_STOCKS = ["VNM", "ACB", "BCM"]  # Test subset

OUTPUT_DIR = "data/Shares_Outstanding"
BASE_URL = "https://www.cophieu68.vn/quote/event_calc_volume.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_html(symbol: str, timeout: int = 30) -> str | None:
    """Lay HTML cua trang event_calc_volume."""
    url = f"{BASE_URL}?id={symbol.lower()}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = "utf-8"
        if r.status_code != 200:
            return None
        return r.text
    except requests.RequestException as e:
        print(f"  [HTTP ERROR] {e}")
        return None


def parse_table(html: str) -> list[dict]:
    """
    Trich bang co cot 'Ngay bo sung' va 'Co phieu Luu Hanh'.

    HTML thuc te cua cophieu68:
    - Header cot cuoi co 2 nhan trong 1 cell: "Ngày bổ sungCổ phiếu Lưu Hành = (CPNY-CPQ)"
    - Data cells cung co 2 gia tri trong 1 cell: "30/01/2007166,950,000"
    - Can tach bang regex: dd/mm/yyyy + so co dau phay
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    # Tim bang co header chua ca 2 cum tu khoa
    target = None
    for tbl in tables:
        txt = tbl.get_text(" ", strip=True)
        if "Ngày bổ sung" in txt and "Lưu Hành" in txt:
            if target is None or len(tbl.find_all("tr")) > len(target.find_all("tr")):
                target = tbl

    if not target:
        return []

    # Tim column index cua cell header chua ca "Ngày bổ sung" + "Lưu Hành"
    date_col = -1
    vol_col = -1
    for tr in target.find_all("tr")[:5]:
        for i, c in enumerate(tr.find_all(["th", "td"])):
            t = c.get_text(strip=True)
            if "Ngày bổ sung" in t and "Lưu Hành" in t:
                # Cot nay chua ca 2 nhan -> data o cung 1 cell, tach bang regex
                date_col = i
                vol_col = i
                break
        if date_col >= 0:
            break

    if date_col < 0:
        return []

    data = []
    for tr in target.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) <= date_col:
            continue
        cell_text = cells[date_col].get_text(" ", strip=True)
        # Bo qua row header/sub-header
        if "Ngày bổ sung" in cell_text:
            continue
        # Regex: dd/mm/yyyy theo sau la so co dau phay
        m = re.search(r"(\d{2}/\d{2}/\d{4})\s*([0-9,]+)", cell_text)
        if m:
            data.append({
                "Ngay bo sung": m.group(1),
                "Co phieu luu hanh": m.group(2),
            })

    return data


def parse_single_listing_fallback(html: str) -> list[dict]:
    """
    Fallback cho ma niem yet 1 lan (BCM, PLX...).
    Trich tu body text theo regex.

    Luu y: HTML co the chua <strong>, <br>, <span>... nen regex can
    "skip" qua tags. Dung BeautifulSoup de loc text sach truoc.
    """
    # Strip HTML de text sach
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    date_m = re.search(r"Ngày niêm yết:\s*(\d{2}/\d{2}/\d{4})", text)
    vol_m = re.search(r"Khối lượng niêm yết lần đầu:\s*([0-9,]+)", text)
    if date_m and vol_m:
        return [{"Ngay bo sung": date_m.group(1), "Co phieu luu hanh": vol_m.group(1)}]
    return []


def crawl_one(symbol: str, output_dir: str = OUTPUT_DIR) -> tuple[int, str]:
    """Crawl 1 ma. Tra ve (so_records, status)."""
    html = fetch_html(symbol)
    if html is None:
        return 0, "HTTP_FAIL"

    data = parse_table(html)
    if not data:
        data = parse_single_listing_fallback(html)
        if not data:
            return 0, "NO_DATA"

    os.makedirs(output_dir, exist_ok=True)
    path = f"{output_dir}/{symbol}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Ngay bo sung", "Co phieu luu hanh"])
        w.writeheader()
        w.writerows(data)
    return len(data), "OK"


def main():
    if len(sys.argv) > 1:
        symbols = [s.upper() for s in sys.argv[1:]]
    else:
        symbols = VN30_STOCKS

    print(f"=== Test requests + BeautifulSoup cho {len(symbols)} ma ===\n")
    t0 = time.time()
    ok, fail, total_records = 0, 0, 0
    for sym in symbols:
        ts = time.time()
        n, status = crawl_one(sym)
        elapsed = time.time() - ts
        total_records += n
        if status == "OK":
            ok += 1
            tag = f"[OK {n} rec]"
        else:
            fail += 1
            tag = f"[{status}]"
        print(f"{tag:<14} {sym:<6} ({elapsed:.2f}s)")

    print(f"\n=== Xong: {ok} OK, {fail} FAIL, {total_records} records tong ===")
    print(f"Tong thoi gian: {time.time() - t0:.1f}s (TB { (time.time() - t0) / len(symbols):.2f}s / ma)")


if __name__ == "__main__":
    main()
