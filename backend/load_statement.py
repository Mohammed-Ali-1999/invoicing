import pandas as pd
import os
# No need for io.StringIO if reading directly from .xlsx file path

# --- Define File Paths ---
raw_statement_file = "NFS STMNT 240425.xlsx" # <--- Changed extension
structured_statement_file = "structured_statement.csv" # Output remains CSV

print(f"Loading raw statement data from: {raw_statement_file}")

# Check if the raw statement file exists
if not os.path.exists(raw_statement_file):
    print(f"Error: Raw supplier statement file not found at {raw_statement_file}.")
    print("Please make sure your supplier statement is named supplier_statement.xlsx in the project folder.") # <--- Updated message
    exit()

try:
    # --- Robust Loading from Excel ---
    # Load the supplier statement XLSX using pandas
    # Use sheet_name=0 to read the first sheet, or sheet_name='Sheet1' for a specific name
    # Use skiprows if there's a fixed number of introductory rows before the data
    # Use header=... if the actual header row is not the very first line after skipping
    # You might need to adjust sheet_name, skiprows, and header based on your file!
    df_statement = pd.read_excel(
        raw_statement_file,
        sheet_name=0,     # Change if your data is on a different sheet (0=first sheet)
        skiprows=0,       # Number of rows to skip at the beginning (adjust if needed)
        header=0          # Row number to use as header (0-indexed, adjust if needed)
        # openpyxl is the default engine for .xlsx, so engine='openpyxl' is usually not needed
    )

    # --- Identify the Correct Columns ---
    # Find the actual column names in the DataFrame after loading.
    # This step is similar to before, but now we look at Excel columns.
    # You might need to manually check your XLSX file to get these exact names.
    # Example: If a column is named 'Invoice #', use that here.
    expected_id_col_raw = "Expected Invoice ID"   # Name in the raw XLSX header
    expected_total_col_raw = "Expected Total Amount" # Name in the raw XLSX header

    # --- Basic Validation (Ensure needed columns exist after loading) ---
    if expected_id_col_raw not in df_statement.columns:
         print(f"Error: Statement XLSX must contain '{expected_id_col_raw}' column.")
         exit()

    # --- Data Cleaning, Standardization, and Selection ---

    # Define standard names for the structured output CSV
    standardized_id_col = "Expected Invoice ID"     # Name in structured_statement.csv
    standardized_total_col = "Expected Total Amount" # Name in structured_statement.csv

    # Create a new DataFrame with only the columns we need, using standardized names
    # Handle case where the total column might be missing in the raw data
    cols_to_select = {}
    if expected_id_col_raw in df_statement.columns:
         cols_to_select[expected_id_col_raw] = standardized_id_col
    else:
         # This case should be caught by the validation above, but good practice
         print(f"Internal Error: '{expected_id_col_raw}' not found after validation.")
         exit()

    if expected_total_col_raw in df_statement.columns:
        cols_to_select[expected_total_col_raw] = standardized_total_col
        print(f"Found total column '{expected_total_col_raw}'.")
    else:
        print(f"Warning: Total column '{expected_total_col_raw}' not found. Total amount reconciliation will not be possible for all entries.")
        # Add the column with NaNs if it was missing
        df_statement[expected_total_col_raw] = pd.NA


    # Select and rename columns
    # Ensure we only select columns that were actually found/added (e.g. total might be missing)
    actual_cols_to_select = {raw_name: std_name for raw_name, std_name in cols_to_select.items() if raw_name in df_statement.columns}
    df_structured = df_statement[list(actual_cols_to_select.keys())].rename(columns=actual_cols_to_select)


    # Ensure the ID column is treated as string and strip whitespace
    df_structured[standardized_id_col] = df_structured[standardized_id_col].astype(str).str.strip()

    # Safely convert the total column to numeric, handling common non-numeric issues
    if standardized_total_col in df_structured.columns:
        # Convert to string first to use string operations like replace
        df_structured[standardized_total_col] = df_structured[standardized_total_col].astype(str)
        # Remove common currency symbols, commas, etc. BEFORE converting to number
        df_structured[standardized_total_col] = df_structured[standardized_total_col].str.replace('[£$€,]', '', regex=True) # Add or remove symbols based on your data
        df_structured[standardized_total_col] = df_structured[standardized_total_col].str.strip() # Remove spaces again
        # Convert to numeric, coercing errors to NaN
        df_structured[standardized_total_col] = pd.to_numeric(df_structured[standardized_total_col], errors='coerce')
    else:
        # If the total column was missing entirely and added as NA, ensure it's numeric type for consistency
        df_structured[standardized_total_col] = pd.to_numeric(df_structured[standardized_total_col], errors='coerce')


    # --- Filter Rows ---
    # Remove rows where the Invoice ID is missing or looks invalid after cleaning
    initial_row_count = len(df_structured)
    df_structured.dropna(subset=[standardized_id_col], inplace=True) # Remove rows where ID is missing/NaN
    # Additional checks for string values that might indicate non-data rows after cleaning
    df_structured = df_structured[df_structured[standardized_id_col] != 'None']
    df_structured = df_structured[df_structured[standardized_id_col] != '']
    # You might add more filters here based on typical non-data values you observe

    rows_removed = initial_row_count - len(df_structured)
    if rows_removed > 0:
        print(f"Removed {rows_removed} rows that did not contain a valid '{standardized_id_col}'.")


    print(f"Successfully processed and structured {len(df_structured)} statement records.")

    # --- Save Structured Data ---
    df_structured.to_csv(structured_statement_file, index=False)
    print(f"\nStructured statement data saved to {structured_statement_file}")

# Specific error for missing Excel library
except ImportError:
    print("\nError: 'openpyxl' library not found.")
    print("Please install it by running: pip install openpyxl")
    exit()
except FileNotFoundError:
     print(f"Error: Raw supplier statement file not found at {raw_statement_file}.")
     exit()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    # You might want to print the full traceback for debugging
    # import traceback
    # traceback.print_exc()
    exit()