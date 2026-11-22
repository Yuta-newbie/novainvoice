import os
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm

from config import Config
from database.db import get_db, get_company_settings

def generate_invoice_pdf(invoice_id, output_path=None):
    """
    Generates a professional GST Tax Invoice PDF using ReportLab.
    Strictly follows Indian GST invoice layout requirements.
    No emojis used. Brownish/warm bronze theme styling.
    """
    conn = get_db()
    try:
        # Fetch invoice header
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, c.name AS customer_name, c.phone AS customer_phone,
                   c.email AS customer_email, c.address AS customer_address,
                   c.state AS customer_state, c.gstin AS customer_gstin
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            WHERE i.invoice_id = ?
        """, (invoice_id,))
        invoice = cursor.fetchone()
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found.")

        # Fetch invoice items
        cursor.execute("""
            SELECT it.*, p.product_name, p.description AS product_desc
            FROM invoice_items it
            JOIN products p ON it.product_id = p.product_id
            WHERE it.invoice_id = ?
            ORDER BY it.item_id ASC
        """, (invoice_id,))
        items = cursor.fetchall()
    finally:
        conn.close()

    company = get_company_settings()

    if output_path is None:
        os.makedirs(Config.PDF_DIR, exist_ok=True)
        filename = f"{invoice['invoice_number']}.pdf"
        output_path = os.path.join(Config.PDF_DIR, filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    # Styles
    styles = getSampleStyleSheet()
    
    # Custom palette
    c_primary = colors.HexColor('#27211C')     # Dark espresso
    c_accent = colors.HexColor('#B45309')      # Warm bronze
    c_text_dark = colors.HexColor('#1F1A15')   # Deep dark text
    c_text_muted = colors.HexColor('#6B5E53')  # Muted taupe
    c_bg_light = colors.HexColor('#F8F5F2')    # Warm cream background
    c_border = colors.HexColor('#E2D9D0')      # Subtle beige border

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=c_text_muted
    )
    
    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=c_text_dark
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_text_dark
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1  # Centered
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=c_text_dark
    )

    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=c_text_dark,
        alignment=2  # Right-aligned
    )

    story = []

    # 1. Top Header Row (Company Branding & TAX INVOICE title)
    header_data = [
        [
            Paragraph(f"<b>{company['name']}</b>", title_style),
            Paragraph("<b>TAX INVOICE</b>", ParagraphStyle('TaxInv', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=c_accent, alignment=2))
        ],
        [
            Paragraph(f"{company['tagline']}<br/>{company['address']}<br/>Phone: {company['phone']} | Email: {company['email']}<br/>GSTIN: <b>{company['gstin']}</b> | State: {company['state']} ({company['state_code']})", subtitle_style),
            Paragraph(f"<b>Invoice No:</b> {invoice['invoice_number']}<br/><b>Invoice Date:</b> {invoice['invoice_date']}<br/><b>Payment Status:</b> {invoice['payment_status']}<br/><b>Payment Method:</b> {invoice['payment_method'] or 'N/A'}", ParagraphStyle('InvMeta', fontName='Helvetica', fontSize=9, leading=13, textColor=c_text_dark, alignment=2))
        ]
    ]

    header_table = Table(header_data, colWidths=[310, 213])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=4, spaceAfter=10))

    # 2. Bill To & Jurisdiction Block
    is_inter = bool(invoice['is_inter_state'])
    tax_type_label = "Inter-State (Integrated GST - IGST)" if is_inter else "Intra-State (Central GST + State GST)"

    cust_gstin_display = invoice['customer_gstin'] if invoice['customer_gstin'] else "Unregistered Consumer"
    
    bill_to_data = [
        [
            Paragraph("<b>BILLED TO (CUSTOMER DETAILS)</b>", ParagraphStyle('BilledH', fontName='Helvetica-Bold', fontSize=9, textColor=c_accent)),
            Paragraph("<b>TAX JURISDICTION DETAILS</b>", ParagraphStyle('JurisH', fontName='Helvetica-Bold', fontSize=9, textColor=c_accent))
        ],
        [
            Paragraph(f"<b>{invoice['customer_name']}</b><br/>{invoice['customer_address'] or 'N/A'}<br/>State: {invoice['customer_state']}<br/>Phone: {invoice['customer_phone']}<br/>GSTIN: {cust_gstin_display}", body_style),
            Paragraph(f"<b>Supply Type:</b> {tax_type_label}<br/><b>Place of Supply:</b> {invoice['customer_state']}<br/><b>Supplier State:</b> {company['state']} ({company['state_code']})<br/><b>Reverse Charge:</b> No", body_style)
        ]
    ]

    bill_to_table = Table(bill_to_data, colWidths=[260, 263])
    bill_to_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg_light),
        ('BOX', (0, 0), (-1, -1), 0.5, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(bill_to_table)
    story.append(Spacer(1, 14))

    # 3. Line Items Table
    # Table columns: Sr, Description, Unit Price, Qty, Taxable Amt, GST Rate, Tax Amt, Total
    item_rows = [[
        Paragraph("Sr.", table_header_style),
        Paragraph("Product Description", table_header_style),
        Paragraph("Unit Price (Rs)", table_header_style),
        Paragraph("Qty", table_header_style),
        Paragraph("Taxable (Rs)", table_header_style),
        Paragraph("GST %", table_header_style),
        Paragraph("Tax (Rs)", table_header_style),
        Paragraph("Total (Rs)", table_header_style)
    ]]

    for idx, item in enumerate(items, 1):
        item_rows.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(f"<b>{item['product_name']}</b>", table_cell_style),
            Paragraph(f"{item['price']:.2f}", table_cell_right),
            Paragraph(str(item['quantity']), table_cell_right),
            Paragraph(f"{item['taxable_amount']:.2f}", table_cell_right),
            Paragraph(f"{item['gst_rate']:.1f}%", table_cell_right),
            Paragraph(f"{item['tax_amount']:.2f}", table_cell_right),
            Paragraph(f"{item['total']:.2f}", table_cell_right)
        ])

    item_col_widths = [24, 169, 58, 32, 65, 45, 60, 70]
    items_table = Table(item_rows, colWidths=item_col_widths, repeatRows=1)
    
    items_style = [
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
    ]
    # Alternating row colors
    for r in range(1, len(item_rows)):
        bg = colors.white if r % 2 != 0 else c_bg_light
        items_style.append(('BACKGROUND', (0, r), (-1, r), bg))

    items_table.setStyle(TableStyle(items_style))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Summary & Calculations Block
    # Left column: Notes / Terms / GST summary
    # Right column: Subtotal, CGST, SGST, IGST, Grand Total
    
    if is_inter:
        tax_rows_text = f"<b>IGST:</b> Rs. {invoice['igst_amount']:.2f}"
    else:
        tax_rows_text = f"<b>CGST:</b> Rs. {invoice['cgst_amount']:.2f}<br/><b>SGST:</b> Rs. {invoice['sgst_amount']:.2f}"

    notes_text = invoice['notes'] if invoice['notes'] else "Goods once sold will not be taken back or exchanged. Standard warranty applies."

    terms_paragraph = Paragraph(
        f"<b>Terms & Conditions:</b><br/>{notes_text}<br/><br/>"
        "Certified that the particulars given above are true and correct. Computer generated invoice.",
        subtitle_style
    )

    totals_data = [
        [Paragraph("<b>Subtotal (Taxable):</b>", body_style), Paragraph(f"Rs. {invoice['subtotal']:.2f}", table_cell_right)],
    ]
    
    if not is_inter:
        totals_data.append([Paragraph("<b>CGST:</b>", body_style), Paragraph(f"Rs. {invoice['cgst_amount']:.2f}", table_cell_right)])
        totals_data.append([Paragraph("<b>SGST:</b>", body_style), Paragraph(f"Rs. {invoice['sgst_amount']:.2f}", table_cell_right)])
    else:
        totals_data.append([Paragraph("<b>IGST:</b>", body_style), Paragraph(f"Rs. {invoice['igst_amount']:.2f}", table_cell_right)])

    totals_data.append([Paragraph("<b>Total Tax:</b>", body_style), Paragraph(f"Rs. {invoice['gst_amount']:.2f}", table_cell_right)])
    totals_data.append([Paragraph("<b>Grand Total:</b>", ParagraphStyle('GrandH', fontName='Helvetica-Bold', fontSize=10, textColor=c_accent)), Paragraph(f"<b>Rs. {invoice['grand_total']:.2f}</b>", ParagraphStyle('GrandV', fontName='Helvetica-Bold', fontSize=11, textColor=c_accent, alignment=2))])

    totals_table = Table(totals_data, colWidths=[110, 110])
    totals_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, c_border),
        ('BACKGROUND', (0, 0), (-1, -2), c_bg_light),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FEF3C7')),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    summary_data = [
        [terms_paragraph, totals_table]
    ]
    summary_table = Table(summary_data, colWidths=[293, 230])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(KeepTogether(summary_table))
    story.append(Spacer(1, 20))

    # 5. Signatory Block
    sig_data = [
        [
            Paragraph("Customer Acknowledgment<br/><br/><br/>_______________________<br/>Receiver Signature", subtitle_style),
            Paragraph(f"For <b>{company['name']}</b><br/><br/><br/>_______________________<br/>Authorized Signatory", ParagraphStyle('AuthSig', fontName='Helvetica', fontSize=9, leading=12, alignment=2, textColor=c_text_dark))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[260, 263])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(KeepTogether(sig_table))

    doc.build(story)
    return output_path

