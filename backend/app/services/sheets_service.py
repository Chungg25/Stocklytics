import gspread
from google.oauth2.service_account import Credentials
import os
import logging

logger = logging.getLogger(__name__)

# Google Sheet ID
SHEET_ID = "1HefYKffJNNO37wkDOQoQgyjqxienSUC4j7u7_IwDoWg"

# Define default groups if sheet is empty
DEFAULT_GROUPS = {
    "Top 50 US": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "LLY", "AVGO", "V",
        "JPM", "UNH", "MA", "XOM", "JNJ", "PG", "HD", "COST", "MRK", "NFLX",
        "ABBV", "AMD", "ADBE", "CVX", "CRM", "KO", "PEP", "ORCL", "TMO", "BAC",
        "ACN", "MCD", "WMT", "CSCO", "DIS", "INTU", "PM", "QCOM", "TXN", "GE",
        "CAT", "VZ", "AMAT", "DHR", "ISRG", "PFE", "INTC", "UNP", "HON", "IBM"
    ],
    "Communication Services": ["META", "GOOGL", "NFLX", "TMUS", "CMCSA", "VZ", "T", "DIS"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "BKNG"],
    "Consumer Defensive": ["PG", "COST", "KO", "PEP", "WMT", "PM", "MDLZ", "CL"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX"],
    "Financial Services": ["JPM", "V", "MA", "BAC", "MS", "GS", "WFC", "AXP"],
    "Healthcare": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "DHR", "PFE", "ABT"],
    "Industrials": ["GE", "CAT", "UNP", "HON", "RTX", "LMT", "UPS", "DE"],
    "Technology": ["MSFT", "AAPL", "NVDA", "AVGO", "CSCO", "ORCL", "ADBE", "AMD", "QCOM", "TXN"],
    "Utilities": ["NEE", "SO", "DUK", "D", "AEP", "SRE", "EXC"]
}

def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Check parent dir or current dir for credentials.json
    cred_path = "credentials.json"
    if not os.path.exists(cred_path) and os.path.exists("../credentials.json"):
        cred_path = "../credentials.json"
        
    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"credentials.json not found in current directory or parent directory.")

    creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
    return gspread.authorize(creds)

def load_groups():
    """Reads groups from Google Sheets. If empty, populates defaults first."""
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Fetch all values
        data = worksheet.get_all_values()
        
        # If sheet is empty or only has empty rows
        if not data or len(data) == 0 or (len(data) == 1 and not data[0]):
            logger.info("Google Sheet is empty. Initializing with default groups...")
            save_groups(DEFAULT_GROUPS)
            return DEFAULT_GROUPS

        # Parse column-based layout
        groups = {}
        headers = data[0]
        
        # Initialize dictionary keys
        for h in headers:
            if h.strip():
                groups[h.strip()] = []
                
        # Fill in rows
        for row in data[1:]:
            for idx, cell in enumerate(row):
                if idx < len(headers):
                    header = headers[idx].strip()
                    ticker = cell.strip().upper()
                    if header and ticker:
                        groups[header].append(ticker)
                        
        return groups
    except Exception as e:
        logger.error(f"Error loading groups from Google Sheets: {e}", exc_info=True)
        # Fallback to defaults if API error
        return DEFAULT_GROUPS

def save_groups(groups_dict):
    """Saves the groups dictionary to Google Sheet in column-based format."""
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Clear existing sheet content
        worksheet.clear()
        
        if not groups_dict:
            return
            
        headers = list(groups_dict.keys())
        
        # Find maximum number of items in any group
        max_rows = max(len(tickers) for tickers in groups_dict.values())
        
        # Prepare grid data
        grid = [headers]
        for row_idx in range(max_rows):
            row_data = []
            for h in headers:
                tickers = groups_dict[h]
                if row_idx < len(tickers):
                    row_data.append(tickers[row_idx])
                else:
                    row_data.append("")
            grid.append(row_data)
            
        # Write to sheet in a single call
        worksheet.update("A1", grid)
        logger.info("Successfully saved groups to Google Sheets.")
    except Exception as e:
        logger.error(f"Error saving groups to Google Sheets: {e}", exc_info=True)
        raise e
