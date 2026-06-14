"""
Financial Statement Downloader using vnstock library
Lấy Bảng CĐKT, Báo cáo KQKD, Báo cáo LCTT theo quý cho VN30.

Ưu điểm so với `vn30_crawler.py` (Selenium):
- Ổn định, không phụ thuộc layout Vietstock
- Nhanh hơn nhiều (1-2s / mã thay vì 2-5 phút)
- Tự gộp 3 bảng (KQKD + CĐKT + LCTT) theo từng mã

Hạn chế:
- Bản miễn phí chỉ lấy được ~8 kỳ gần nhất (~2 năm)
- Muốn nhiều kỳ hơn cần mua gói Insiders Program của vnstock

Output:
- data/finance/<SYMBOL>.csv — 1 file / mã, gồm cả 3 bảng gộp theo cột 'item'
- data/finance/<SYMBOL>_income.csv, _balance.csv, _cashflow.csv — tách riêng từng bảng
"""

import os
import sys
import time
from vnstock import Vnstock

# VN30 (danh sách hiện hành, có BCM)
VN30_STOCKS = [
    "ACB", "BCM", "BID", "CTG", "DGC", "FPT", "GAS", "GVR", "HDB", "HPG",
    "LPB", "MBB", "MSN", "MWG", "PLX", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
]

OUTPUT_DIR = "data/finance"
PERIOD = "quarter"   # 'quarter' hoặc 'year'
SOURCE = "VCI"


def fetch_one(stock, kind: str):
    """Lấy 1 bảng tài chính. kind ∈ {income_statement, balance_sheet, cash_flow}."""
    return getattr(stock.finance, kind)(period=PERIOD)


def download_one(symbol: str, output_dir: str = OUTPUT_DIR) -> bool:
    try:
        print(f"[..] {symbol} ", end="", flush=True)
        t0 = time.time()
        stock = Vnstock().stock(symbol=symbol, source=SOURCE)

        income = fetch_one(stock, "income_statement")
        balance = fetch_one(stock, "balance_sheet")
        cashflow = fetch_one(stock, "cash_flow")

        if income is None or income.empty:
            print("[FAIL] income empty")
            return False

        os.makedirs(output_dir, exist_ok=True)
        # Ghi từng bảng riêng
        income.to_csv(f"{output_dir}/{symbol}_income.csv", index=False)
        balance.to_csv(f"{output_dir}/{symbol}_balance.csv", index=False)
        cashflow.to_csv(f"{output_dir}/{symbol}_cashflow.csv", index=False)

        # Gộp 3 bảng theo cột 'item' (label tiếng Việt)
        merged = income.merge(
            balance.drop(columns=[c for c in balance.columns if c not in ["item"] + list(income.columns[3:])]),
            on="item", how="outer", suffixes=("", "_b")
        ) if False else income  # tạm: giữ merged = income, người dùng tự nối nếu cần

        # Gộp đúng: các cột quý giống nhau, chỉ khác phần chỉ tiêu
        # income, balance, cashflow đều có 'item', 'item_en', 'item_id' + các cột Q
        # Ta nối theo item, lấy tất cả cột quý
        quarter_cols = [c for c in income.columns if c not in ("item", "item_en", "item_id")]
        merged = income[["item", "item_en", "item_id"] + quarter_cols].copy()
        merged = merged.rename(columns={c: f"KQKD_{c}" for c in quarter_cols})
        if not balance.empty:
            bal_q = [c for c in balance.columns if c not in ("item", "item_en", "item_id")]
            bal_part = balance[["item"] + bal_q].rename(columns={c: f"CĐKT_{c}" for c in bal_q})
            merged = merged.merge(bal_part, on="item", how="outer")
        if not cashflow.empty:
            cf_q = [c for c in cashflow.columns if c not in ("item", "item_en", "item_id")]
            cf_part = cashflow[["item"] + cf_q].rename(columns={c: f"LCTT_{c}" for c in cf_q})
            merged = merged.merge(cf_part, on="item", how="outer")

        merged.to_csv(f"{output_dir}/{symbol}.csv", index=False)

        print(f"[OK] {len(income)} dong KQKD, {len(balance)} dong CĐKT, {len(cashflow)} dong LCTT ({time.time()-t0:.1f}s)")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def main():
    if len(sys.argv) > 1:
        # Cho phép truyền danh sách mã từ CLI
        symbols = [s.upper() for s in sys.argv[1:]]
    else:
        symbols = VN30_STOCKS

    print(f"=== Tai bao cao tai chinh cho {len(symbols)} ma (period={PERIOD}, source={SOURCE}) ===\n")
    ok, fail = 0, 0
    for sym in symbols:
        if download_one(sym):
            ok += 1
        else:
            fail += 1

    print(f"\n=== Xong: {ok} OK, {fail} FAIL / {len(symbols)} ma ===")
    print(f"Output: {OUTPUT_DIR}/<SYMBOL>.csv + <SYMBOL>_{{income,balance,cashflow}}.csv")


if __name__ == "__main__":
    main()
