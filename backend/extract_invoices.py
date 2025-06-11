import os
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import pandas as pd
import glob # To find files in a folder

def get_next_filename(base_name):
    """Generate next available filename with incrementing number."""
    counter = 1
    filename = base_name
    while os.path.exists(filename):
        name, ext = os.path.splitext(base_name)
        filename = f"{name}_{counter}{ext}"
        counter += 1
    return filename

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

if not endpoint or not key:
    print("Error: Azure endpoint or key not found. Make sure your .env file is correct.")
    exit()

# Create a DocumentAnalysisClient
document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# Define the folder containing your sample invoices
invoices_folder = "./invoice_temp_storage/"

# List to store extracted data
extracted_data = []

# Find all PDF and image files in the folder
invoice_files = glob.glob(os.path.join(invoices_folder, "*.pdf")) + \
                glob.glob(os.path.join(invoices_folder, "*.png")) + \
                glob.glob(os.path.join(invoices_folder, "*.jpg")) + \
                glob.glob(os.path.join(invoices_folder, "*.jpeg"))

print(f"Looking for invoices in: {invoices_folder}")
print("\nFound these files:")
for file in invoice_files:
    print(f"- {file}")

if not invoice_files:
    print(f"No invoice files found in {invoices_folder}. Please add some sample invoices.")
else:
    print(f"\nFound {len(invoice_files)} files to process.")

    # --- Extraction Loop ---
    for invoice_path in invoice_files:
        print(f"\nProcessing invoice: {invoice_path}")
        try:
            # Read the invoice file in binary mode
            with open(invoice_path, "rb") as f:
                invoice_bytes = f.read()

            # Start the analysis operation using the pre-built invoice model
            # The 'prebuilt-invoice' model is specifically trained for invoices
            poller = document_analysis_client.begin_analyze_document("prebuilt-invoice", invoice_bytes)

            # Wait for the analysis to complete
            result = poller.result()

            # --- Parse the Results ---
            # The prebuilt-invoice model extracts various fields.
            # We need to access the 'documents' list in the result,
            # which contains the analyzed document(s) (usually one per file).
            if result.documents:
                # Get the first analyzed document (assuming one invoice per file)
                invoice_document = result.documents[0]

                # Access extracted fields using the fields dictionary
                # The keys here correspond to the field names returned by the model
                invoice_id = invoice_document.fields.get("InvoiceId")
                invoice_date = invoice_document.fields.get("InvoiceDate")
                total_amount = invoice_document.fields.get("InvoiceTotal")
                net_total = invoice_document.fields.get("SubTotal")
                tax_total = invoice_document.fields.get("TotalTax")

                # For descriptions or line items, it's slightly more complex
                # The 'Items' field is a list of objects (line items)
                items = invoice_document.fields.get("Items")
                descriptions = []
                if items and items.value:
                     for item in items.value:
                         # Each item object has fields like 'Description', 'Quantity', 'Amount', etc.
                         description_field = item.value.get("Description")
                         if description_field and description_field.value:
                             descriptions.append(description_field.value)
                 # Join descriptions into a single string for simplicity in this PoC
                descriptions_text = "; ".join(descriptions) if descriptions else "No description extracted"


                # Store the extracted data
                extracted_data.append({
                    "File Path": invoice_path,
                    "Invoice ID": invoice_id.value if invoice_id else None,
                    "Invoice Date": invoice_date.value if invoice_date else None,
                    "Net Total": str(net_total.value).replace('Â£', '£') if net_total and net_total.value else "0",
                    "Tax Total": str(tax_total.value).replace('Â£', '£') if tax_total and tax_total.value else "0",
                    "Total Amount": str(total_amount.value).replace('Â£', '£') if total_amount and total_amount.value else "0",
                    "Descriptions": descriptions_text
                })

                print(f"  - Extracted ID: {extracted_data[-1]['Invoice ID']}")
                print(f"  - Extracted Date: {extracted_data[-1]['Invoice Date']}")
                print(f"  - Extracted Net Total: {extracted_data[-1]['Net Total']}")
                print(f"  - Extracted Tax Total: {extracted_data[-1]['Tax Total']}")
                print(f"  - Extracted Total: {extracted_data[-1]['Total Amount']}")
                print(f"  - Extracted Descriptions (partial): {extracted_data[-1]['Descriptions'][:100]}...") # Print first 100 chars

            else:
                print(f"  - No document found in the result for {invoice_path}. Extraction might have failed.")

        except Exception as e:
            print(f"  - Error processing {invoice_path}: {e}")
            extracted_data.append({
                "File Path": invoice_path,
                "Invoice ID": "ERROR",
                "Invoice Date": "ERROR",
                "Net Total": "ERROR",
                "Tax Total": "ERROR",
                "Total Amount": "ERROR",
                "Descriptions": f"Error: {e}"
            })


    # Convert extracted data to a pandas DataFrame
    df_extracted = pd.DataFrame(extracted_data)

    # Display the extracted data
    print("\n--- Extracted Data ---")
    print(df_extracted.to_string()) # Use to_string() to see all rows if many

    # Save extracted data to a CSV with incrementing number if file exists
    output_file = get_next_filename("extracted_invoices/extracted_invoices.csv")
    df_extracted.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nExtracted data saved to {output_file}")
