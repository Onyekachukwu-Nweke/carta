import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union
from sqlalchemy import create_engine, Engine

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# CARTA — Customer Agent for Reordering, Trading & Automation
########################
########################
########################

import difflib

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

dotenv.load_dotenv()

# ── Model ─────────────────────────────────────────────────────────────────────

_provider = OpenAIProvider(
    base_url=os.getenv("OPENAI_BASE_URL", "https://openai.vocareum.com/v1"),
    api_key=os.getenv("UDACITY_OPENAI_API_KEY"),
)
_model = OpenAIModel(os.getenv("OPENAI_MODEL", "gpt-4o-mini"), provider=_provider)

# ── Shared helpers ────────────────────────────────────────────────────────────

_price_map: Dict[str, float] = {item["item_name"]: item["unit_price"] for item in paper_supplies}


def _get_unit_price(item_name: str) -> float:
    return _price_map.get(item_name, 0.0)


def _apply_bulk_discount(unit_price: float, quantity: int) -> float:
    if quantity >= 500:
        return unit_price * 0.85
    elif quantity >= 100:
        return unit_price * 0.90
    elif quantity >= 50:
        return unit_price * 0.95
    return unit_price


# Words too generic to distinguish between catalog items.
_STOP_WORDS = {"a4", "a3", "a5", "a6", "paper", "sheet", "sheets", "of", "the", "and", "in", "with", "high", "quality"}

def _find_catalog_match(customer_term: str) -> tuple:
    """
    Three-stage fuzzy match: exact → sequence ratio → keyword Jaccard.
    Returns (canonical_name, confidence) or (None, 0.0).
    """
    catalog_names = list(_price_map.keys())
    term_lower = customer_term.lower().strip()

    # Stage 1: case-insensitive exact
    for name in catalog_names:
        if name.lower() == term_lower:
            return name, 1.0

    # Stage 2: difflib sequence ratio with a keyword-confirmation guard.
    # High threshold (0.65) plus we require at least one significant word from the
    # customer term to appear in the matched name — prevents "printer paper" matching
    # "Poster paper" because both share the " paper" suffix.
    seq_scores = sorted(
        ((n, difflib.SequenceMatcher(None, term_lower, n.lower()).ratio()) for n in catalog_names),
        key=lambda x: -x[1],
    )
    top_name, top_score = seq_scores[0]
    if top_score >= 0.65:
        term_sig = {w for w in term_lower.split() if w not in _STOP_WORDS and len(w) >= 4}
        top_sig = {w for w in top_name.lower().split() if w not in _STOP_WORDS and len(w) >= 4}
        if not term_sig or (term_sig & top_sig):
            return top_name, round(top_score, 2)

    # Stage 3: Jaccard on significant words
    # e.g. "A4 glossy paper" → {"glossy"} matches "Glossy paper" → {"glossy"}
    term_words = {w for w in term_lower.split() if w not in _STOP_WORDS and len(w) >= 4}
    if term_words:
        word_scores = []
        for name in catalog_names:
            name_words = {w for w in name.lower().split() if w not in _STOP_WORDS and len(w) >= 4}
            if not name_words:
                continue
            intersection = term_words & name_words
            union = term_words | name_words
            score = len(intersection) / len(union)
            # Boost when all customer keywords appear in the name
            if intersection == term_words:
                score = min(score + 0.25, 1.0)
            word_scores.append((name, score))
        word_scores.sort(key=lambda x: -x[1])
        if word_scores and word_scores[0][1] >= 0.3:
            return word_scores[0][0], round(word_scores[0][1], 2)

    # Stage 4: substring containment fallback
    for name in catalog_names:
        name_lower = name.lower()
        if name_lower in term_lower or term_lower in name_lower:
            return name, 0.5

    return None, 0.0


def disambiguate_item_name(customer_item_name: str) -> dict:
    """
    Map a customer-provided item description to the nearest canonical catalog name.
    Always call this before any inventory, price, or fulfillment tool.
    """
    canonical, confidence = _find_catalog_match(customer_item_name)
    if canonical:
        return {
            "matched": True,
            "canonical_name": canonical,
            "confidence": confidence,
            "unit_price": _price_map[canonical],
        }
    suggestions = difflib.get_close_matches(customer_item_name, list(_price_map.keys()), n=3, cutoff=0.2)
    return {
        "matched": False,
        "canonical_name": None,
        "confidence": 0.0,
        "suggestions": suggestions or [],
    }


# ── Inventory Agent ───────────────────────────────────────────────────────────

inventory_agent = Agent(
    _model,
    name="inventory_agent",
    system_prompt=(
        "You are the Inventory Specialist for Munder Difflin Paper Company. "
        "IMPORTANT: For every item name received from the customer, call disambiguate_item_name "
        "first to resolve it to the exact catalog name before any other tool call. "
        "Then check stock levels and restock when needed. "
        "Before restocking, always call check_cash_balance to confirm the company can afford it. "
        "When restocking, order enough to bring stock to at least 600 units above the current level. "
        "Return a structured summary listing: canonical item name, current stock, whether it was "
        "restocked, restocked quantity, and estimated delivery date."
    ),
)

inventory_agent.tool_plain(disambiguate_item_name)


@inventory_agent.tool_plain
def check_inventory(item_name: str, date: str) -> dict:
    """Return current stock and min-stock threshold for an item."""
    result = get_stock_level(item_name, date)
    stock = int(result["current_stock"].iloc[0])
    inv_row = pd.read_sql(
        "SELECT min_stock_level FROM inventory WHERE item_name = :n",
        db_engine,
        params={"n": item_name},
    )
    min_stock = int(inv_row["min_stock_level"].iloc[0]) if not inv_row.empty else 100
    return {
        "item_name": item_name,
        "current_stock": stock,
        "min_stock_level": min_stock,
        "needs_restock": stock < min_stock,
    }


@inventory_agent.tool_plain
def get_all_inventory_status(date: str) -> dict:
    """Return stock levels for every tracked item as of a given date."""
    return get_all_inventory(date)


@inventory_agent.tool_plain
def check_cash_balance(date: str) -> dict:
    """Return current cash balance so restocking decisions are cash-aware."""
    balance = get_cash_balance(date)
    return {"date": date, "cash_balance": round(balance, 2), "can_restock": balance > 0}


@inventory_agent.tool_plain
def restock_item(item_name: str, quantity: int, date: str) -> dict:
    """Place a stock-order transaction to replenish an item."""
    unit_price = _get_unit_price(item_name)
    if unit_price == 0.0:
        return {"success": False, "error": f"Unknown item: {item_name}"}
    total_cost = round(quantity * unit_price, 2)
    txn_id = create_transaction(item_name, "stock_orders", quantity, total_cost, date)
    return {
        "success": True,
        "transaction_id": txn_id,
        "item_name": item_name,
        "quantity_restocked": quantity,
        "total_cost": total_cost,
        "estimated_delivery": get_supplier_delivery_date(date, quantity),
    }


# ── Quote Agent ───────────────────────────────────────────────────────────────

quote_agent = Agent(
    _model,
    name="quote_agent",
    system_prompt=(
        "You are the Quoting Specialist for Munder Difflin Paper Company. "
        "IMPORTANT: For every item name, call disambiguate_item_name first to get the canonical name "
        "before calling any other tool. "
        "Generate accurate quotes by referencing historical quote data and applying bulk discounts: "
        "5% for ≥50 units, 10% for ≥100 units, 15% for ≥500 units. "
        "If an item was recently restocked (indicated in the request), quote it as available with "
        "a note that delivery will be on the restock delivery date. "
        "Always provide a clear line-item breakdown with base price, discount %, discounted unit price, "
        "and grand total. After producing the quote, always call save_quote to persist it."
    ),
)

quote_agent.tool_plain(disambiguate_item_name)


@quote_agent.tool_plain
def get_quote_history(search_terms: List[str]) -> List[dict]:
    """Search historical quotes that match the provided terms."""
    return search_quote_history(search_terms, limit=3)


@quote_agent.tool_plain
def check_item_stock(item_name: str, date: str) -> dict:
    """Check available stock for a single item before quoting."""
    result = get_stock_level(item_name, date)
    return {"item_name": item_name, "current_stock": int(result["current_stock"].iloc[0])}


@quote_agent.tool_plain
def save_quote(
    total_amount: float,
    explanation: str,
    job_type: str,
    order_size: str,
    event_type: str,
    date: str,
) -> dict:
    """Persist a generated quote to the quotes table so future searches can find it."""
    row = pd.DataFrame([{
        "request_id": None,
        "total_amount": round(total_amount, 2),
        "quote_explanation": explanation,
        "order_date": date,
        "job_type": job_type,
        "order_size": order_size,
        "event_type": event_type,
    }])
    row.to_sql("quotes", db_engine, if_exists="append", index=False)
    return {"saved": True, "total_amount": round(total_amount, 2), "date": date}


@quote_agent.tool_plain
def calculate_item_quote(item_name: str, quantity: int) -> dict:
    """Return the discounted price for a line item."""
    unit_price = _get_unit_price(item_name)
    if unit_price == 0.0:
        return {"error": f"Unknown item: {item_name}"}
    disc_price = _apply_bulk_discount(unit_price, quantity)
    discount_pct = round((1 - disc_price / unit_price) * 100)
    return {
        "item_name": item_name,
        "quantity": quantity,
        "base_unit_price": unit_price,
        "discount_pct": discount_pct,
        "discounted_unit_price": round(disc_price, 4),
        "line_total": round(disc_price * quantity, 2),
    }


# ── Order Agent ───────────────────────────────────────────────────────────────

order_agent = Agent(
    _model,
    name="order_agent",
    system_prompt=(
        "You are the Order Fulfillment Specialist for Munder Difflin Paper Company. "
        "IMPORTANT: For every item name, call disambiguate_item_name first to get the canonical name. "
        "For each item: call verify_stock, then call lookup_item_price (use discounted price if provided, "
        "otherwise use catalog price), then call fulfill_order to record the sale, and "
        "call check_delivery_timeline for the ETA. "
        "PARTIAL FULFILLMENT: If available stock is less than requested, fulfill the available quantity "
        "immediately via fulfill_order, then clearly report the shortfall quantity as a back-order "
        "(e.g. '228 units back-ordered — restock pending, delivery in 4 days'). "
        "Continue processing all other items even if one has insufficient stock."
    ),
)

order_agent.tool_plain(disambiguate_item_name)


@order_agent.tool_plain
def lookup_item_price(item_name: str) -> dict:
    """Return the catalog unit price for an item."""
    price = _get_unit_price(item_name)
    if price == 0.0:
        return {"error": f"Unknown item: {item_name}"}
    return {"item_name": item_name, "catalog_unit_price": price}


@order_agent.tool_plain
def verify_stock(item_name: str, quantity: int, date: str) -> dict:
    """Confirm sufficient stock is available for an order line."""
    result = get_stock_level(item_name, date)
    available = int(result["current_stock"].iloc[0])
    return {
        "item_name": item_name,
        "requested": quantity,
        "available": available,
        "sufficient": available >= quantity,
    }


@order_agent.tool_plain
def check_delivery_timeline(date: str, quantity: int) -> dict:
    """Estimate delivery date based on order quantity."""
    return {
        "order_date": date,
        "quantity": quantity,
        "estimated_delivery": get_supplier_delivery_date(date, quantity),
    }


@order_agent.tool_plain
def fulfill_order(item_name: str, quantity: int, unit_price: float, date: str) -> dict:
    """Record a sales transaction for a confirmed order line."""
    total_price = round(quantity * unit_price, 2)
    txn_id = create_transaction(item_name, "sales", quantity, total_price, date)
    return {
        "success": True,
        "transaction_id": txn_id,
        "item_name": item_name,
        "quantity_sold": quantity,
        "total_price": total_price,
        "estimated_delivery": get_supplier_delivery_date(date, quantity),
    }


# ── CARTA Orchestrator ────────────────────────────────────────────────────────

_catalog = "\n".join(
    f"  - {item['item_name']} (${item['unit_price']:.2f}/unit)"
    for item in paper_supplies
)

carta = Agent(
    _model,
    name="carta",
    system_prompt=(
        "You are CARTA — Customer Agent for Reordering, Trading & Automation — the central "
        "orchestration system for Munder Difflin Paper Company.\n\n"
        "For every customer request follow these steps:\n"
        "1. Call call_inventory_agent with the requested items and date. It will check stock and "
        "   restock low items. Note which items were restocked and their delivery dates.\n"
        "2. Call call_quote_agent with the full customer request, date, AND a note listing any "
        "   restocked items with their delivery dates, so the quote agent can price them as "
        "   'available by [date]' rather than refusing to quote.\n"
        "3. Call call_order_agent with the item names, quantities, and discounted prices from the "
        "   quote, and the date. It will fulfill available stock immediately and report any "
        "   back-order shortfalls.\n"
        "4. If call_order_agent reports back-order shortfalls, call call_inventory_agent again "
        "   with only those items to trigger restocking of the exact shortfall quantities.\n"
        "5. Optionally call get_financial_report for an updated financial snapshot.\n"
        "6. Return a clear, professional summary: quote breakdown with discounts, what was fulfilled "
        "   immediately, what is back-ordered and when it will arrive.\n\n"
        f"Product catalog (use exact item names):\n{_catalog}"
    ),
)


@carta.tool_plain
def call_inventory_agent(items: List[str], date: str) -> str:
    """Delegate inventory checks and restocking to the Inventory Agent."""
    prompt = (
        f"Date: {date}. Check stock for: {', '.join(items)}. "
        "For any item below its min_stock_level, restock it with 600 units. "
        "Return a summary of current stock and any restock actions taken."
    )
    result = inventory_agent.run_sync(prompt)
    return result.output


@carta.tool_plain
def call_quote_agent(request: str, date: str, restock_notes: str = "") -> str:
    """Delegate quote generation to the Quote Agent.

    restock_notes: optional string describing items just restocked and their delivery dates,
    so the quote agent can price them as available-by-date rather than out-of-stock.
    """
    restock_section = f"\nRestock context: {restock_notes}" if restock_notes else ""
    prompt = (
        f"Date: {date}.\nCustomer request: {request}{restock_section}\n"
        "Search quote history for comparable orders, then produce a detailed quote "
        "with bulk discounts, showing: item name, quantity, base unit price, discount %, "
        "discounted unit price, and line total. Include the grand total. "
        "For restocked items, quote them as available on their delivery date. "
        "After generating the quote, call save_quote to persist it."
    )
    result = quote_agent.run_sync(prompt)
    return result.output


@carta.tool_plain
def get_financial_report(date: str) -> dict:
    """Return a full financial snapshot: cash balance, inventory value, and top sellers."""
    report = generate_financial_report(date)
    return {
        "date": date,
        "cash_balance": report["cash_balance"],
        "inventory_value": report["inventory_value"],
        "total_assets": report["total_assets"],
        "top_selling_products": report["top_selling_products"],
    }


@carta.tool_plain
def call_order_agent(order_details: str, date: str) -> str:
    """Delegate order fulfillment to the Order Agent."""
    prompt = (
        f"Date: {date}.\nOrder to fulfil: {order_details}\n"
        "Verify stock for each item, record the sale transactions, "
        "and return the estimated delivery date for each item."
    )
    result = order_agent.run_sync(prompt)
    return result.output


def call_carta(request: str) -> str:
    """Process a customer request through the full CARTA pipeline."""
    result = carta.run_sync(request)
    return result.output


# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date").reset_index(drop=True)
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        try:
            response = call_carta(request_with_date)
        except Exception as e:
            response = f"[CARTA error: {e}]"
            print(f"ERROR on request {idx+1}: {e}")

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
