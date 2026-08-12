import glob
import os
import re
import pandas as pd
import openpyxl
from typing import List, Dict, Any
from solution.extractors.extract_projects import clean_client_name
from solution.extractors.money_parser import parse_date, parse_money

def extract_receivables_ageing() -> List[Dict[str, Any]]:
    path = 'documents/workbooks/Receivables_Ageing.xlsx'
    df = pd.read_excel(path, sheet_name='AR Ageing')
    records = []
    
    for _, row in df.iterrows():
        inv_no = str(row.get('Invoice No', '')).strip()
        client = str(row.get('Client', '')).strip()
        clean_client = clean_client_name(client)
        inv_date = parse_date(str(row.get('Invoice Date', '')))
        invoiced = parse_money(row.get('Invoiced (INR)', 0))
        status = str(row.get('Status', '')).strip()
        received = parse_money(row.get('Received (INR)', 0))
        outstanding = parse_money(row.get('Outstanding (INR)', 0))
        
        records.append({
            'invoice_no': inv_no,
            'raw_client_name': client,
            'client_name': clean_client,
            'invoice_date': inv_date,
            'invoiced_inr': invoiced,
            'status': status,
            'received_inr': received,
            'outstanding_inr': outstanding
        })
        
    return records

def extract_asset_register() -> List[Dict[str, Any]]:
    path = 'documents/workbooks/Plant_and_Machinery_Register.xlsx'
    if not os.path.exists(path):
        return []
    df = pd.read_excel(path, sheet_name='Plant Register')
    records = []
    
    for _, row in df.iterrows():
        raw_id = row.get('Asset ID')
        if pd.isna(raw_id):
            continue
        try:
            asset_id = int(raw_id)
        except (ValueError, TypeError):
            continue
            
        asset_type = str(row.get('Type', '')).strip()
        make = str(row.get('Make', '')).strip()
        raw_acq = row.get('Acquired')
        acquired_year = int(raw_acq) if pd.notna(raw_acq) and str(raw_acq).isdigit() else 0
        cost = parse_money(row.get('Cost (INR)', 0))
        condition = str(row.get('Condition', '')).strip()
        location = str(row.get('Location', '')).strip()
        ownership = str(row.get('Ownership', '')).strip()
        safety_certified = bool(row.get('Safety Certified', False))
        
        records.append({
            'asset_id': asset_id,
            'asset_type': asset_type,
            'make': make,
            'acquired_year': acquired_year,
            'cost_inr': cost,
            'condition': condition,
            'location': location,
            'ownership': ownership,
            'safety_certified': safety_certified
        })
        
    return records

if __name__ == '__main__':
    ar = extract_receivables_ageing()
    assets = extract_asset_register()
    print(f'Extracted {len(ar)} AR records and {len(assets)} Asset records.')
