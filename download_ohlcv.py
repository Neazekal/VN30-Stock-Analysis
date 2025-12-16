"""
OHLCV Data Downloader using vnstock library
Download historical stock price data from Vietnamese stock market (HOSE, HNX, UPCOM)

Usage:
    python download_ohlcv.py

Requirements:
    pip install vnstock pandas openpyxl
"""

from vnstock import Vnstock
from vnstock import Quote
import pandas as pd
from datetime import datetime, timedelta
import os


def download_ohlcv(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
    interval: str = "1D",
    source: str = "VCI",
    output_format: str = "csv",
    output_dir: str = "data/OLHCV"
) -> pd.DataFrame:
    """
    Download OHLCV (Open, High, Low, Close, Volume) data for a Vietnamese stock.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'VNM', 'VIC', 'ACB', 'FPT')
        start_date: Start date in 'YYYY-MM-DD' format (default: 1 year ago)
        end_date: End date in 'YYYY-MM-DD' format (default: today)
        interval: Time interval - '1D' (daily), '1W' (weekly), '1M' (monthly)
        source: Data source - 'VCI' or 'TCBS'
        output_format: Output file format - 'csv', 'excel', or 'both'
        output_dir: Directory to save output files (default: 'data')
    
    Returns:
        DataFrame with OHLCV data
    """
    # Set default dates if not provided
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    print(f"Downloading OHLCV data for {symbol}...")
    print(f"Period: {start_date} to {end_date}")
    print(f"Interval: {interval}, Source: {source}")
    
    # Initialize vnstock and get historical data
    quote = Quote(symbol=symbol, source=source)
    df = quote.history(start=start_date, end=end_date, interval=interval)
    
    if df is None or df.empty:
        print(f"No data found for {symbol}")
        return pd.DataFrame()
    
    print(f"Downloaded {len(df)} records")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to file
    if output_format in ["csv", "both"]:
        csv_file = os.path.join(output_dir, f"{symbol}.csv")
        df.to_csv(csv_file, index=False)
        print(f"Saved to {csv_file}")
    
    if output_format in ["excel", "both"]:
        excel_file = os.path.join(output_dir, f"{symbol}.xlsx")
        df.to_excel(excel_file, index=False)
        print(f"Saved to {excel_file}")
    
    return df


def download_multiple_stocks(
    symbols: list,
    start_date: str = None,
    end_date: str = None,
    interval: str = "1D",
    source: str = "VCI",
    output_dir: str = "data/OLHCV"
) -> dict:
    """
    Download OHLCV data for multiple stocks.
    
    Args:
        symbols: List of stock ticker symbols
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        interval: Time interval
        source: Data source
        output_dir: Directory to save output files (default: 'data')
    
    Returns:
        Dictionary with symbol as key and DataFrame as value
    """
    results = {}
    
    for symbol in symbols:
        try:
            df = download_ohlcv(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                source=source,
                output_format="csv",
                output_dir=output_dir
            )
            results[symbol] = df
            print(f"✓ {symbol} completed\n")
        except Exception as e:
            print(f"✗ Error downloading {symbol}: {e}\n")
            results[symbol] = pd.DataFrame()
    
    return results


def get_all_listed_symbols(source: str = "VCI") -> pd.DataFrame:
    """
    Get list of all listed stock symbols.
    
    Args:
        source: Data source - 'VCI' or 'TCBS'
    
    Returns:
        DataFrame with listing information
    """
    stock = Vnstock().stock(source=source)
    return stock.listing.all_symbols()


# Example usage
if __name__ == "__main__":
    # Example 1: Download single stock
    # print("=" * 50)
    # print("Example 1: Download single stock (VNM)")
    # print("=" * 50)
    
    # df = download_ohlcv(
    #     symbol="VNM",
    #     start_date="2024-01-01",
    #     end_date="2024-12-15",
    #     interval="1D",
    #     output_format="csv",
    #     output_dir="data"
    # )
    
    # if not df.empty:
    #     print("\nFirst 5 rows:")
    #     print(df.head())
    #     print("\nColumns:", df.columns.tolist())
    
    # Example 2: Download multiple stocks
    # print("\n" + "=" * 50)
    # print("Example 2: Download multiple stocks")
    # print("=" * 50)
    
    # VN30 Index Components (30 stocks)
    symbols = [
        "ACB",   # Asia Commercial Bank
        "BID",   # Bank for Investment and Development
        "CTG",   # Vietnam Commercial Bank for Industry and Trade
        "DGC",   # Ducgiang Chemicals
        "FPT",   # FPT Corp
        "GAS",   # Petrovietnam Gas
        "GVR",   # Vietnam Rubber
        "HDB",   # Ho Chi Minh City Development Bank
        "HPG",   # Hoa Phat Group
        "LPB",   # Fortune Vietnam Joint Stock Commercial Bank
        "MBB",   # Military Commercial Bank
        "MSN",   # Masan Group
        "MWG",   # Mobile World Investment
        "PLX",   # Vietnam National Petroleum
        "SAB",   # Saigon Beer Alcohol Beverage
        "SHB",   # Sai Gon Ha Noi Commercial Bank
        "SSB",   # Southeast Asia Commercial Bank
        "SSI",   # SSI Securities
        "STB",   # Sai Gon Thuong Tin Commercial Bank
        "TCB",   # Techcombank
        "TPB",   # Tien Phong Commercial Bank
        "VCB",   # JSC Bank for Foreign Trade of Vietnam
        "VHM",   # Vinhomes
        "VIB",   # Vietnam International Commercial Bank
        "VIC",   # Vingroup
        "VJC",   # Vietjet Aviation
        "VNM",   # Vinamilk
        "VPB",   # Vietnam Prosperity Bank
        "VRE",   # Vincom Retail
        "BCM",   # Investment and Industrial Development
    ]
    results = download_multiple_stocks(
        symbols=symbols,
        start_date="2020-01-01",
        end_date="2025-12-15",
        output_dir="data/OLHCV"
    )
    
    # Example 3: Get all listed symbols
    # print("\n" + "=" * 50)
    # print("Example 3: Get all listed symbols")
    # print("=" * 50)
    
    # Uncomment to get all symbols
    # all_symbols = get_all_listed_symbols()
    # print(all_symbols.head(10))
