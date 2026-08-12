import re
from datetime import datetime
from typing import Any

NUMBER_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
    'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'twenty-one': 21, 'twenty-two': 22, 'twenty-three': 23, 'twenty-four': 24, 'twenty-five': 25,
    'twenty-six': 26, 'twenty-seven': 27, 'twenty-eight': 28, 'twenty-nine': 29, 'thirty': 30,
    'thirty-one': 31, 'thirty-two': 32, 'thirty-three': 33, 'thirty-four': 34, 'thirty-five': 35,
    'thirty-six': 36, 'thirty-seven': 37, 'thirty-eight': 38, 'thirty-nine': 39, 'forty': 40,
    'forty-one': 41, 'forty-two': 42, 'forty-three': 43, 'forty-four': 44, 'forty-five': 45,
    'forty-six': 46, 'forty-seven': 47, 'forty-eight': 48, 'forty-nine': 49, 'fifty': 50,
    'fifty-one': 51, 'fifty-two': 52, 'fifty-three': 53, 'fifty-four': 54, 'fifty-five': 55,
    'fifty-six': 56, 'fifty-seven': 57, 'fifty-eight': 58, 'fifty-nine': 59, 'sixty': 60,
    'seventy': 70, 'eighty': 80, 'ninety': 90, 'hundred': 100
}

def words_to_number(text: str) -> float:
    """Convert words like 'twenty-three', 'forty', 'six' to numbers."""
    text = text.lower().strip()
    if text in NUMBER_WORDS:
        return float(NUMBER_WORDS[text])
    parts = text.replace('-', ' ').split()
    total = 0
    for p in parts:
        if p in NUMBER_WORDS:
            total += NUMBER_WORDS[p]
    return float(total) if total > 0 else 0.0

def parse_money(val_str: Any) -> int:
    """
    Losslessly parses money strings in Indian notation into exact integer rupees.
    """
    if val_str is None:
        return 0
    if isinstance(val_str, float) and (val_str != val_str): # NaN check
        return 0
    if isinstance(val_str, (int, float)):
        return int(round(val_str))
    
    val = str(val_str).strip()
    val = re.sub(r'[\r\n\t]+', ' ', val)
    
    # 1. Crore pattern: e.g. INR 33.38 Cr, Rs. 18.26 Crore, 200.00 Cr, 20 Cr
    cr_match = re.search(r'(?:INR|Rs\.?|₹)?\s*([\d\.]+)\s*(?:Cr(?:ore)?s?)\b', val, re.IGNORECASE)
    if cr_match:
        num = float(cr_match.group(1))
        return int(round(num * 10_000_000))
    
    # 2. Lakh pattern: e.g. 3,338.00 Lakh, INR 450.5 Lakhs
    lakh_match = re.search(r'(?:INR|Rs\.?|₹)?\s*([\d,\.]+)\s*(?:Lakh(?:s)?|Lac(?:s)?)\b', val, re.IGNORECASE)
    if lakh_match:
        raw_num = lakh_match.group(1).replace(',', '')
        num = float(raw_num)
        return int(round(num * 100_000))
    
    # 3. Direct number with Indian commas or standard format e.g. 33,38,00,000 or 1,944,300,000
    cleaned = re.sub(r'[^\d\.]', '', val)
    if cleaned:
        try:
            return int(round(float(cleaned)))
        except ValueError:
            pass
            
    return 0

def parse_date(date_str: str) -> str:
    """
    Parses various date strings into ISO format YYYY-MM-DD.
    Examples:
      '06/02/2011' -> '2011-02-06'
      '31/03/2026' -> '2026-03-31'
      '2021-03-10' -> '2021-03-10'
      'January 12, 2015' -> '2015-01-12'
      '12 January 2015' -> '2015-01-12'
      '06 Feb 2011' -> '2011-02-06'
    """
    if not date_str:
        return ""
    d_str = str(date_str).strip()
    d_str = re.sub(r'[\r\n\t]+', ' ', d_str)
    
    formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
        '%d %b %Y',
        '%B %d %Y',
        '%b %d %Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(d_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
            
    # Try regex matching YYYY-MM-DD
    iso_match = re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})', d_str)
    if iso_match:
        return f"{iso_match.group(1)}-{iso_match.group(2)}-{iso_match.group(3)}"
        
    dmy_match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', d_str)
    if dmy_match:
        return f"{dmy_match.group(3)}-{dmy_match.group(2)}-{dmy_match.group(1)}"
        
    return d_str

def extract_threshold_rupees(text: str) -> int:
    """
    Extracts threshold amounts from text like 'forty crore', 'twenty-three crore', 'INR 20 Cr', '43 crore', '6 crore', '23.0 Cr', '70cr', '120 Cr'.
    """
    # 1. Numeric with Cr / Crore / cr
    num_cr = re.search(r'(\d+(?:\.\d+)?)\s*(?:cr(?:ore)?s?)\b', text, re.IGNORECASE)
    if num_cr:
        return int(round(float(num_cr.group(1)) * 10_000_000))
        
    # 2. Word with crore e.g. 'forty crore', 'twenty-three crore', 'seventy-three crore', 'twenty six crore'
    words = '(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?'
    word_cr = re.search(rf'({words})\s+crore', text, re.IGNORECASE)
    if word_cr:
        n = words_to_number(word_cr.group(1))
        if n > 0:
            return int(round(n * 10_000_000))
            
    # 3. Numeric with lakh
    num_lakh = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh(?:s)?)\b', text, re.IGNORECASE)
    if num_lakh:
        return int(round(float(num_lakh.group(1)) * 100_000))
        
    return 0
