import glob, fitz, re, openpyxl, os, sys
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))
from solution.extractors.money_parser import parse_money, parse_date

print("=" * 80)
print("INDEPENDENT RAW DOCUMENT VERIFICATION OF THE 6 QUESTIONS")
print("=" * 80)

# Helper to extract project from raw PDF
def parse_raw_ccc(pdf_path):
    doc = fitz.open(pdf_path)
    txt = '\n'.join([p.get_text() for p in doc])
    
    title = re.search(r'Work\s*\n\s*([^\n]+)', txt) or re.search(r'Project Title:\s*([^\n]+)', txt)
    client = re.search(r'Client\s*\n\s*([^\n]+)', txt) or re.search(r'Client Name:\s*([^\n]+)', txt)
    cat = re.search(r'Category\s*\n\s*([^\n]+)', txt) or re.search(r'Category:\s*([^\n]+)', txt)
    val = re.search(r'Executed Value\s*\n\s*([^\n]+)', txt) or re.search(r'Contract Value:\s*([^\n]+)', txt)
    comp = re.search(r'Completion\s*\n\s*([^\n]+)', txt) or re.search(r'Date of Completion:\s*([^\n]+)', txt)
    lead = re.search(r'Project Lead\s*\n\s*([^\n]+)', txt) or re.search(r'Lead Engineer:\s*([^\n]+)', txt)
    
    # Clean client name (remove (psu), (government), etc.)
    cl_name = client.group(1).strip() if client else ''
    cl_name = re.sub(r'\s*\([^)]*\)', '', cl_name).strip()
    
    return {
        'file': pdf_path,
        'title': title.group(1).strip() if title else '',
        'client': cl_name,
        'category': cat.group(1).strip().lower() if cat else '',
        'value': parse_money(val.group(1).strip()) if val else 0,
        'completion': parse_date(comp.group(1).strip()) if comp else None,
        'lead': lead.group(1).strip() if lead else ''
    }

# -------------------------------------------------------------
# Q1: HV-IC-0006 (Lakshya Engineering & Construction shortfall)
# -------------------------------------------------------------
print("\n--- [1] HV-IC-0006: Lakshya Engineering & Construction ---")
wb = openpyxl.load_workbook('documents/workbooks/Receivables_Ageing.xlsx')
ws = wb.active
headers = [str(c.value).strip() if c.value else '' for c in ws[1]]
c_idx = [i for i, h in enumerate(headers) if 'Client' in h or 'Customer' in h or 'Debtor' in h][0]
inv_idx = [i for i, h in enumerate(headers) if 'Invoiced' in h][0]
rec_idx = [i for i, h in enumerate(headers) if 'Received' in h][0]
out_idx = [i for i, h in enumerate(headers) if 'Outstanding' in h][0]

lakshya_invoiced = 0
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[c_idx] and 'Lakshya' in str(row[c_idx]):
        lakshya_invoiced += float(row[inv_idx])

# Parse all 155 raw CCC files
all_raw_projs = [parse_raw_ccc(f) for f in glob.glob('documents/company_completion_certificate/*.pdf')]
lakshya_projs = [p for p in all_raw_projs if 'Lakshya' in p['client']]

lakshya_awarded = sum(p['value'] for p in lakshya_projs)
print(f"Awarded Projects ({len(lakshya_projs)} total): {int(lakshya_awarded):,} INR")
for p in lakshya_projs:
    print(f"  * {p['title']}: {int(p['value']):,} INR")
print(f"Total Invoiced in Receivables: {int(lakshya_invoiced):,} INR")
print(f"Shortfall (Awarded - Invoiced): {int(lakshya_awarded - lakshya_invoiced):,} INR")


# -------------------------------------------------------------
# Q2: HV-IC-0233 (Jaya Desai / Mahanadi Steel Corporation)
# -------------------------------------------------------------
print("\n--- [2] HV-IC-0233: Jaya Desai / Mahanadi Steel Corporation ---")
mahanadi_projs = [p for p in all_raw_projs if 'Mahanadi Steel' in p['client']]
print(f"All Mahanadi Projects ({len(mahanadi_projs)} total):")
sum_all = sum(p['value'] for p in mahanadi_projs)
for p in mahanadi_projs:
    print(f"  * {p['title']} | Lead: {p['lead']} | {int(p['value']):,} INR")
print(f"Sum across ALL client projects: {int(sum_all):,} INR")


# -------------------------------------------------------------
# Q3: HV-IC-0291 (Asha Nair / Pkg-145 -> Mega Infrastructure)
# -------------------------------------------------------------
print("\n--- [3] HV-IC-0291: Asha Nair / Pkg-145 -> Mega Infrastructure ---")
mega_projs = [p for p in all_raw_projs if 'Mega Infrastructure' in p['client']]
print(f"Mega Infrastructure projects ({len(mega_projs)} total):")
for p in mega_projs:
    print(f"  * {p['title']}: {int(p['value']):,} INR")
avg_mega = sum(p['value'] for p in mega_projs) / len(mega_projs)
print(f"Average: {avg_mega:.2f} -> {int(round(avg_mega)):,} INR")


# -------------------------------------------------------------
# Q4: HV-IC-0402 (National Special Projects Office Unpaid)
# -------------------------------------------------------------
print("\n--- [4] HV-IC-0402: National Special Projects Office Unpaid ---")
nspo_inv = 0
nspo_rec = 0
nspo_out = 0
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[c_idx] and 'National Special Projects Office' in str(row[c_idx]):
        nspo_inv += float(row[inv_idx])
        nspo_rec += float(row[rec_idx])
        nspo_out += float(row[out_idx])

print(f"Invoiced: {int(nspo_inv):,} INR")
print(f"Received: {int(nspo_rec):,} INR")
print(f"Outstanding (Invoiced - Received): {int(nspo_out):,} INR")


# -------------------------------------------------------------
# Q5: HV-IC-0368 (Naveen Roy / Pkg-31 STP Days)
# -------------------------------------------------------------
print("\n--- [5] HV-IC-0368: Naveen Roy / Pkg-31 STP Days ---")
pkg31 = [p for p in all_raw_projs if 'Pkg-31' in p['title'] or 'Pkg-31' in p['file']][0]
print(f"Project: {pkg31['title']}")
print(f"Lead: {pkg31['lead']}")
print(f"Completion Date: {pkg31['completion']}")
ref_date = datetime(2021, 3, 10)
comp_dt = datetime.strptime(pkg31['completion'], '%Y-%m-%d')
days = (comp_dt - ref_date).days
print(f"Reference Date: 2021-03-10, Completion Date: {pkg31['completion']}, Days Elapsed: {days}")


# -------------------------------------------------------------
# Q6: HV-IC-0432 (Mahanadi Steel Corporation EPC vs Water Treatment)
# -------------------------------------------------------------
print("\n--- [6] HV-IC-0432: Mahanadi EPC vs Water Treatment ---")
epc_projs = [p for p in mahanadi_projs if 'industrial epc' in p['category'] or 'epc' in p['category']]
wt_projs = [p for p in mahanadi_projs if 'water treatment' in p['category']]

epc_sum = sum(p['value'] for p in epc_projs)
wt_sum = sum(p['value'] for p in wt_projs)

print("Industrial EPC projects:")
for p in epc_projs:
    print(f"  * {p['title']}: {int(p['value']):,} INR")
print(f"Total EPC: {int(epc_sum):,} INR")

print("\nWater Treatment projects:")
for p in wt_projs:
    print(f"  * {p['title']}: {int(p['value']):,} INR")
print(f"Total WT: {int(wt_sum):,} INR")

print(f"\nAbsolute Difference: {int(abs(epc_sum - wt_sum)):,} INR")
