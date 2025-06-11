import pandas as pd
import os
import glob

def get_most_recent_file(pattern):
    """Find the most recent file matching the pattern."""
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)

def get_next_filename(base_name):
    """Generate next available filename with incrementing number."""
    counter = 1
    filename = base_name
    while os.path.exists(filename):
        name, ext = os.path.splitext(base_name)
        filename = f"{name}_{counter}{ext}"
        counter += 1
    return filename

# --- Define File Paths ---
extracted_data_file = get_most_recent_file("extracted_invoices/extracted_invoices*.csv")
statement_file = "supplier_statement.csv"

# --- Load Data ---
if not extracted_data_file:
    print("Error: No extracted invoices file found.")
    print("Please run extract_invoices.py first to generate this file.")
    exit()

print(f"Loading extracted data from: {extracted_data_file}")

try:
    df_extracted = pd.read_csv(extracted_data_file)
    # Ensure Invoice ID is treated as string to avoid issues with numerical IDs
    df_extracted['Invoice ID'] = df_extracted['Invoice ID'].astype(str).str.strip()
    # Convert Total Amount to numeric, handling currency symbols
    df_extracted['Total Amount'] = df_extracted['Total Amount'].apply(
        lambda x: float(str(x).replace('Â£', '').replace('£', '').replace(',', '')) 
        if isinstance(x, (int, float, str)) and str(x).replace('Â£', '').replace('£', '').replace(',', '').replace('.', '', 1).isdigit() 
        else 0.0
    )
    print(f"Successfully loaded {len(df_extracted)} extracted records.")

except Exception as e:
    print(f"Error loading extracted data from {extracted_data_file}: {e}")
    exit()


print(f"Loading supplier statement from: {statement_file}")
if not os.path.exists(statement_file):
    print(f"Error: Supplier statement file not found at {statement_file}.")
    print("Please create the supplier_statement.csv file as described in the previous step.")
    exit()

try:
    df_statement = pd.read_csv(statement_file)
    # Ensure column names match your CSV file
    expected_id_col = "Expected Invoice ID"
    expected_total_col = "Expected Total Amount"

    if expected_id_col not in df_statement.columns or expected_total_col not in df_statement.columns:
         print(f"Error: Statement CSV must contain '{expected_id_col}' and '{expected_total_col}' columns.")
         exit()

    # Ensure Expected Invoice ID is treated as string
    df_statement[expected_id_col] = df_statement[expected_id_col].astype(str).str.strip()
    # Convert Expected Total Amount to numeric, handling currency symbols
    df_statement[expected_total_col] = df_statement[expected_total_col].apply(
        lambda x: float(str(x).replace('Â£', '').replace('£', '').replace(',', '')) 
        if isinstance(x, (int, float, str)) and str(x).replace('Â£', '').replace('£', '').replace(',', '').replace('.', '', 1).isdigit() 
        else 0.0
    )
    print(f"Successfully loaded {len(df_statement)} statement records.")

except Exception as e:
    print(f"Error loading supplier statement from {statement_file}: {e}")
    exit()


# --- Reconciliation Logic ---
print("\n--- Performing Reconciliation ---")

# Prepare Data for Comparison
# Create dictionaries for quick lookups, handling potential None/NaN values and stripping whitespace
extracted_dict = {
    row["Invoice ID"]: row
    for index, row in df_extracted.iterrows()
    if pd.notna(row["Invoice ID"]) and row["Invoice ID"] != "ERROR" and row["Invoice ID"] != "None" # Handle various potential bad values
}

print("\nExtracted Invoice IDs:", list(extracted_dict.keys()))

statement_dict = {
    row[expected_id_col]: row
    for index, row in df_statement.iterrows()
    if pd.notna(row[expected_id_col]) and row[expected_id_col] != "None"
}

print("Statement Invoice IDs:", list(statement_dict.keys()))

# --- Perform Comparisons ---

# 1. Check for Missing Invoices (In statement but not extracted)
missing_invoices = []
for statement_id in statement_dict:
    if statement_id not in extracted_dict:
        missing_invoices.append(statement_id)

if missing_invoices:
    print(f"\nMissing Invoices (in statement but not extracted): {', '.join(missing_invoices)}")
else:
    print("\nNo missing invoices found.")

# 2. Check for Extra Invoices (Extracted but not in statement)
extra_invoices = []
for extracted_id in extracted_dict:
     if extracted_id not in statement_dict:
         extra_invoices.append(extracted_id)

if extra_invoices:
     print(f"\nExtra Invoices (extracted but not in statement): {', '.join(extra_invoices)}")
else:
     print("\nNo extra invoices found.")


# 3. Check for Total Amount Discrepancies (Only for invoices found in both)
discrepancies = []
total_extracted_matched = 0.0
total_expected_matched = 0.0

for statement_id, statement_row in statement_dict.items():
    if statement_id in extracted_dict:
        extracted_row = extracted_dict[statement_id]

        expected_total = statement_row[expected_total_col]
        extracted_total = extracted_row["Total Amount"]

        # Check if both totals are valid numbers before comparing
        if pd.notna(expected_total) and pd.notna(extracted_total):
            total_expected_matched += expected_total
            total_extracted_matched += extracted_total

            if abs(expected_total - extracted_total) > 0.01: # Allow for small floating point differences
                discrepancies.append({
                    "Invoice ID": statement_id,
                    "Expected Total": expected_total,
                    "Extracted Total": extracted_total
                })
        else:
             # Handle cases where one or both totals were not successfully loaded/extracted as numbers
             print(f"  - Could not compare totals for {statement_id}: Expected or Extracted Total is not a valid number.")


if discrepancies:
    print("\nTotal Amount Discrepancies (for invoices found in both):")
    for disc in discrepancies:
        print(f"  - Invoice ID: {disc['Invoice ID']}, Expected: £{disc['Expected Total']:.2f}, Extracted: £{disc['Extracted Total']:.2f}")
else:
     print("\nNo significant total amount discrepancies found for matched invoices.")

# 4. Overall Totals (Optional but helpful)
print("\nOverall Totals:")
# Sum extracted totals, excluding NaNs from conversion errors
print(f"  - Total of all extracted invoices (successfully parsed total): £{df_extracted['Total Amount'].sum():.2f}")
print(f"  - Total of expected invoices (from statement): £{df_statement[expected_total_col].sum():.2f}")

print(f"  - Total of extracted invoices found in statement: £{total_extracted_matched:.2f}")
print(f"  - Total of expected invoices found in extraction: £{total_expected_matched:.2f}") # Should be the same as total_extracted_matched for matched invoices

# Save reconciliation results to CSV
reconciliation_results = []

# Add missing invoices
for invoice_id in missing_invoices:
    reconciliation_results.append({
        "Invoice ID": invoice_id,
        "Status": "Missing",
        "Expected Total": f"£{df_statement[df_statement[expected_id_col] == invoice_id][expected_total_col].iloc[0]:.2f}",
        "Extracted Total": "£0.00",
        "Difference": f"£{-df_statement[df_statement[expected_id_col] == invoice_id][expected_total_col].iloc[0]:.2f}"
    })

# Add extra invoices
for invoice_id in extra_invoices:
    reconciliation_results.append({
        "Invoice ID": invoice_id,
        "Status": "Extra",
        "Expected Total": "£0.00",
        "Extracted Total": f"£{df_extracted[df_extracted['Invoice ID'] == invoice_id]['Total Amount'].iloc[0]:.2f}",
        "Difference": f"£{df_extracted[df_extracted['Invoice ID'] == invoice_id]['Total Amount'].iloc[0]:.2f}"
    })

# Add discrepancies
for disc in discrepancies:
    reconciliation_results.append({
        "Invoice ID": disc["Invoice ID"],
        "Status": "Discrepancy",
        "Expected Total": f"£{disc['Expected Total']:.2f}",
        "Extracted Total": f"£{disc['Extracted Total']:.2f}",
        "Difference": f"£{disc['Extracted Total'] - disc['Expected Total']:.2f}"
    })

# Add matched invoices (those that exist in both and have matching amounts)
for statement_id in statement_dict:
    if statement_id in extracted_dict and statement_id not in [d["Invoice ID"] for d in discrepancies]:
        reconciliation_results.append({
            "Invoice ID": statement_id,
            "Status": "Matched",
            "Expected Total": f"£{statement_dict[statement_id][expected_total_col]:.2f}",
            "Extracted Total": f"£{extracted_dict[statement_id]['Total Amount']:.2f}",
            "Difference": "£0.00"
        })

# Add summary row
reconciliation_results.append({
    "Invoice ID": "SUMMARY",
    "Status": "Totals",
    "Expected Total": f"£{df_statement[expected_total_col].sum():.2f}",
    "Extracted Total": f"£{df_extracted['Total Amount'].sum():.2f}",
    "Difference": f"£{df_extracted['Total Amount'].sum() - df_statement[expected_total_col].sum():.2f}"
})

# Convert to DataFrame and save
df_results = pd.DataFrame(reconciliation_results)
# Replace any remaining None or NaN values with £0.00
df_results = df_results.fillna("£0.00")
results_file = get_next_filename("reconcilliation_results/reconciliation_results.csv")
df_results.to_csv(results_file, index=False, encoding='utf-8-sig')
print(f"\nReconciliation results saved to {results_file}")

print("\nReconciliation complete.")