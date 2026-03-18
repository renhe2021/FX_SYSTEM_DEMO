# Convert USD_SIGNAL JSON (.txt) to CSV and Excel
# Usage: python convert_json_to_csv.py [V2|V3]
import pandas as pd
import json
import sys
import io
from pathlib import Path

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Determine version from command-line arg (default: V2)
version = sys.argv[1] if len(sys.argv) > 1 else 'V2'
base_dir = Path(__file__).parent

input_file = str(base_dir / f'USD_SIGNAL_{version}.txt')
output_csv = str(base_dir / f'USD_SIGNAL_{version}.csv')
output_excel = str(base_dir / f'USD_SIGNAL_{version}.xlsx')

print("=" * 60)
print("Reading JSON file...")
print("=" * 60)

# Read JSON file
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Done! Total records: {len(data)}")

# Convert to DataFrame
df = pd.DataFrame(data)

print(f"\nColumns: {list(df.columns)}")
print(f"\nData preview:")
print(df.head())

# Save to CSV
df.to_csv(output_csv, index=False, encoding='utf-8-sig')
print(f"\nSaved CSV: {output_csv}")

# Save to Excel
df.to_excel(output_excel, index=False)
print(f"Saved Excel: {output_excel}")

print("\n" + "=" * 60)
print("Conversion complete!")
print("=" * 60)
