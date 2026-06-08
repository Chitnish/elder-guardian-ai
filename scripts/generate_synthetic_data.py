"""Generate realistic synthetic elder transaction CSVs for demo."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUTPUT_DIR = Path(__file__).parent.parent / 'data' / 'synthetic'

NORMAL_PAYEES = [
    ('Kroger Grocery', 'groceries', 40, 120, [9, 10, 11]),
    ('CVS Pharmacy', 'pharmacy', 10, 80, [10, 14, 15]),
    ('Walgreens', 'pharmacy', 15, 90, [10, 14, 15]),
    ('Electric Company', 'utilities', 80, 180, [9]),
    ('Gas Company', 'utilities', 40, 90, [9]),
    ('Shell Gas Station', 'transport', 30, 60, [10, 11, 14]),
    ('Denny''s Restaurant', 'dining', 15, 35, [11, 12, 17]),
    ('McDonald''s', 'dining', 8, 20, [11, 12, 17]),
    ('Medicare Supplement', 'insurance', 140, 170, [9]),
    ('Netflix', 'entertainment', 12, 16, [20]),
    ('Sunshine Retirement Rent', 'housing', 880, 900, [9]),
]

def random_amount(low, high):
    return round(random.uniform(low, high), 2)

def generate_normal(start: date, days: int) -> list[dict]:
    rows = []
    current = start
    while current <= start + timedelta(days=days):
        num_txns = random.randint(1, 3)
        for _ in range(num_txns):
            payee, category, low, high, hours = random.choice(NORMAL_PAYEES)
            rows.append({
                'date': current.isoformat(),
                'amount': random_amount(low, high),
                'payee': payee,
                'category': category,
                'hour_of_day': random.choice(hours),
            })
        current += timedelta(days=random.randint(1, 3))
    return rows

def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date','amount','payee','category','hour_of_day'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {len(rows)} rows to {path.name}')

def generate_normal_baseline() -> None:
    rows = generate_normal(date(2024, 1, 1), 90)
    write_csv(OUTPUT_DIR / 'normal_baseline.csv', rows)

def generate_grooming_drain() -> None:
    rows = generate_normal(date(2024, 1, 1), 60)
    # Grooming phase: days 21-60, small increasing transfers to Michael Johnson
    grooming_amounts = [50, 75, 100, 150, 200, 250, 300]
    grooming_date = date(2024, 1, 21)
    for amount in grooming_amounts:
        rows.append({
            'date': grooming_date.isoformat(),
            'amount': amount,
            'payee': 'Michael Johnson',
            'category': 'transfer',
            'hour_of_day': random.randint(19, 22),
        })
        grooming_date += timedelta(days=random.randint(5, 8))
    # Drain phase: days 61-90, large rapid transfers
    drain_amounts = [500, 750, 1200, 2500, 3800, 5000, 7500, 10000]
    drain_date = date(2024, 3, 1)
    for amount in drain_amounts:
        rows.append({
            'date': drain_date.isoformat(),
            'amount': amount,
            'payee': random.choice(['MJ Investments LLC', 'Offshore Account Transfer']),
            'category': 'transfer',
            'hour_of_day': random.randint(21, 23),
        })
        drain_date += timedelta(days=random.randint(2, 4))
    rows.sort(key=lambda r: r['date'])
    write_csv(OUTPUT_DIR / 'grooming_then_drain.csv', rows)

def generate_sudden_exploitation() -> None:
    rows = generate_normal(date(2024, 1, 1), 70)
    # Sudden large transfers starting day 71
    sudden_amounts = [8500, 12000, 15000, 22000, 18500, 25000]
    sudden_date = date(2024, 3, 12)
    for amount in sudden_amounts:
        rows.append({
            'date': sudden_date.isoformat(),
            'amount': amount,
            'payee': random.choice(['Wire Transfer Intl', 'Crypto Exchange Transfer', 'Western Union Transfer']),
            'category': 'transfer',
            'hour_of_day': random.randint(1, 3),
        })
        sudden_date += timedelta(days=random.randint(2, 3))
    rows.sort(key=lambda r: r['date'])
    write_csv(OUTPUT_DIR / 'sudden_exploitation.csv', rows)

if __name__ == '__main__':
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_normal_baseline()
    generate_grooming_drain()
    generate_sudden_exploitation()
    print('Done.')