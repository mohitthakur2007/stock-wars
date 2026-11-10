
import csv
import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = BASE_DIR / "data" / "ind_nifty100list.csv"


def load_nifty100():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"NIFTY 100 CSV not found: {CSV_PATH}"
        )

    companies = []

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("NIFTY 100 CSV has no headers")

        # Normalize CSV headers to handle minor naming differences.
        headers = {
            header.strip().lower(): header
            for header in reader.fieldnames
        }

        def find_column(*names):
            for name in names:
                if name.lower() in headers:
                    return headers[name.lower()]
            raise ValueError(
                f"Missing CSV column. Expected one of: {names}"
            )

        name_col = find_column("Company Name")
        symbol_col = find_column("Symbol")
        industry_col = find_column("Industry")

        for row in reader:
            name = (row.get(name_col) or "").strip()
            symbol = (row.get(symbol_col) or "").strip()
            industry = (row.get(industry_col) or "").strip()

            if not name or not symbol:
                continue

            companies.append({
                "name": name,
                "symbol": symbol,
                "sector": industry or "Other",
            })

    # Avoid duplicate stock symbols.
    unique = {
        company["symbol"]: company
        for company in companies
    }

    companies = list(unique.values())

    if len(companies) < 15:
        raise ValueError(
            f"Only {len(companies)} companies loaded. "
            "Check the CSV format and contents."
        )

    return companies


def generate_companies(count):
    universe = load_nifty100()

    if count < 10 or count > 15:
        raise ValueError("Company count must be between 10 and 15")

    if count > len(universe):
        raise ValueError("Not enough companies in the universe")

    selected = random.sample(universe, count)

    companies = []

    for index, source in enumerate(selected):
        base_value = random.randrange(1000, 4001, 500)

        companies.append({
            "id": f"C{index + 1:02d}",

            # Actual NIFTY 100 identity, hidden during auction.
            "name": source["name"],
            "symbol": source["symbol"],
            "sector": source["sector"],

            # Limited information shown during auction.
            "business": source["sector"],
            "risk": random.choice(["Low", "Medium", "High"]),
            "growth": random.choice([
                "Moderate", "Strong", "Very High"
            ]),
            "revenue_trend": random.choice([
                "Increasing", "Stable", "Declining"
            ]),

            # Virtual game valuation, not actual market valuation.
            "base_value": base_value,
            "hidden_trait": random.choice([
                "Strong cash reserves",
                "Major expansion planned",
                "New product breakthrough",
                "Regulatory challenges",
                "High debt burden",
                "International expansion",
                "No major hidden development"
            ]),
            "hidden_multiplier": random.choice([
                0.75, 0.85, 1.00, 1.15, 1.20, 1.30, 1.40
            ]),

            "owner_id": None,
            "sold_price": None,
            "final_value": base_value,
        })

    random.shuffle(companies)
    return companies
