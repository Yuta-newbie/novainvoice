import re
from decimal import Decimal, ROUND_HALF_UP

def round_currency(val):
    """Accurate decimal-safe monetary rounding to 2 decimal places."""
    if val is None:
        return Decimal('0.00')
    d = Decimal(str(val))
    return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

def validate_phone(phone_str):
    """Validates Indian phone numbers (10 digits, optional +91 or 0 prefix)."""
    if not phone_str:
        return False, "Phone number is required."
    cleaned = re.sub(r'[\s\-+]', '', phone_str)
    if cleaned.startswith('91') and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith('0') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if re.match(r'^[6-9]\d{9}$', cleaned):
        return True, cleaned
    return False, "Invalid Indian mobile number. Must be 10 digits starting with 6, 7, 8, or 9."

def validate_email(email_str):
    """Validates email format if provided."""
    if not email_str or not email_str.strip():
        return True, ""  # Optional field
    email_str = email_str.strip()
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if re.match(pattern, email_str):
        return True, email_str
    return False, "Invalid email address format."

def validate_gstin(gstin_str):
    """
    Validates Indian 15-character GSTIN format:
    2-digit state code + 10-char PAN + 1 entity num + 'Z' + 1 checksum char.
    Optional field for un-registered retail customers.
    """
    if not gstin_str or not gstin_str.strip():
        return True, ""
    gstin_str = gstin_str.strip().upper()
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if re.match(pattern, gstin_str):
        return True, gstin_str
    return False, "Invalid GSTIN format. Expected 15 characters (e.g. 09AABCS1429B1Z1)."

def calculate_gst_breakdown(taxable_amount, gst_rate, is_inter_state):
    """
    Computes GST amounts based on tax jurisdiction:
    Intra-state: CGST = Rate/2, SGST = Rate/2, IGST = 0
    Inter-state: IGST = Full Rate, CGST = 0, SGST = 0
    """
    t_amt = Decimal(str(taxable_amount))
    rate = Decimal(str(gst_rate))
    
    if is_inter_state:
        cgst = Decimal('0.00')
        sgst = Decimal('0.00')
        igst = (t_amt * rate) / Decimal('100.0')
    else:
        cgst = (t_amt * (rate / Decimal('2.0'))) / Decimal('100.0')
        sgst = (t_amt * (rate / Decimal('2.0'))) / Decimal('100.0')
        igst = Decimal('0.00')
        
    total_tax = cgst + sgst + igst
    total_amount = t_amt + total_tax

    return {
        'taxable_amount': round_currency(t_amt),
        'cgst_amount': round_currency(cgst),
        'sgst_amount': round_currency(sgst),
        'igst_amount': round_currency(igst),
        'tax_amount': round_currency(total_tax),
        'total_amount': round_currency(total_amount)
    }

