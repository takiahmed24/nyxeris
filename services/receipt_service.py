"""Receipt and Invoice Generation Service for Nyxeris.
Generates 100% white-labeled Nyxeris PDF invoices and HTML emails.
Strict requirement: Zero Whop or third-party payment gateway branding is shown to customer.
"""

import os
import datetime
from pathlib import Path
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from config import settings, RECEIPTS_DIR


def generate_nyxeris_receipt_pdf(order: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Generates an itemized, high-end PDF receipt for a Nyxeris order.
    
    Args:
        order: Dictionary containing order information.
        items: List of order items.
        
    Returns:
        Absolute file path to the generated PDF.
    """
    order_id = order["order_id"]
    file_name = f"receipt_{order_id}.pdf"
    pdf_path = RECEIPTS_DIR / file_name

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=f"Nyxeris Receipt - {order_id}",
        author="Nyxeris Official Store"
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette (Nyxeris Editorial Luxury)
    brand_primary = colors.HexColor("#1f1919")     # Nyxeris Deep Charcoal
    brand_accent = colors.HexColor("#324632")      # Forest Olive Accent
    brand_cyan = colors.HexColor("#324632")        # Forest Olive
    text_dark = colors.HexColor("#1f1919")         # Deep Charcoal Dark text
    text_muted = colors.HexColor("#767676")        # Muted grey text
    border_color = colors.HexColor("#e8e8e8")      # Divider hairline border
    table_header_bg = colors.HexColor("#f7f5f4")   # Table header background
    badge_green = colors.HexColor("#2e7d32")       # Paid confirmation green

    # Typography Styles
    style_brand = ParagraphStyle(
        "NyxerisBrand",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=brand_primary,
        spaceAfter=2
    )

    style_tagline = ParagraphStyle(
        "NyxerisTagline",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=text_muted
    )

    style_invoice_title = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=2,  # Right align
        textColor=brand_primary
    )

    style_invoice_meta = ParagraphStyle(
        "InvoiceMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=13,
        alignment=2,  # Right align
        textColor=text_muted
    )

    style_section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading4"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=brand_accent,
        spaceAfter=4
    )

    style_body = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark
    )

    style_body_bold = ParagraphStyle(
        "BodyTextBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=text_dark
    )

    style_table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=brand_primary
    )

    style_table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=text_dark
    )

    style_table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=text_dark
    )

    style_table_cell_right = ParagraphStyle(
        "TableCellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        alignment=2,
        textColor=text_dark
    )

    style_paid_badge = ParagraphStyle(
        "PaidBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        alignment=2,
        textColor=badge_green
    )

    story = []

    # 1. Header Section: Brand Logo & Invoice Metadata
    created_date = order.get("created_at", datetime.datetime.now().strftime("%B %d, %Y"))
    if isinstance(created_date, str) and "T" in created_date:
        try:
            dt = datetime.datetime.fromisoformat(created_date.replace("Z", "+00:00"))
            created_date = dt.strftime("%B %d, %Y")
        except Exception:
            pass

    header_left = [
        Paragraph("NYXERIS", style_brand),
        Paragraph(settings.STORE_TAGLINE, style_tagline),
        Paragraph(f"Official Storefront: {settings.BASE_URL}", style_tagline),
        Paragraph(f"Support: {settings.STORE_SUPPORT_EMAIL}", style_tagline),
    ]

    header_right = [
        Paragraph("OFFICIAL PURCHASE RECEIPT", style_invoice_title),
        Paragraph(f"<b>Order Number:</b> {order_id}", style_invoice_meta),
        Paragraph(f"<b>Date Issued:</b> {created_date}", style_invoice_meta),
        Paragraph(f"<b>Payment Status:</b> <font color='{badge_green}'>PAID & VERIFIED</font>", style_invoice_meta),
        Paragraph(f"<b>Fulfillment:</b> {order.get('fulfillment_status', 'Processing').capitalize()}", style_invoice_meta),
    ]

    header_table = Table(
        [[header_left, header_right]],
        colWidths=[4.0 * inch, 3.2 * inch]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_accent, spaceBefore=4, spaceAfter=14))

    # 2. Customer & Physical Shipping Address Info
    ship_name = order.get("customer_name", "Valued Customer")
    ship_line1 = order.get("shipping_address_line1", "")
    ship_line2 = order.get("shipping_address_line2", "")
    ship_city = order.get("shipping_city", "")
    ship_state = order.get("shipping_state", "")
    ship_zip = order.get("shipping_postal_code", "")
    ship_country = order.get("shipping_country", "")
    ship_method = order.get("shipping_method", "Standard Express Insured Delivery")
    carrier = order.get("carrier")
    tracking = order.get("tracking_number")

    customer_info = [
        Paragraph("BILLED TO", style_section_title),
        Paragraph(f"<b>{ship_name}</b>", style_body_bold),
        Paragraph(f"Email: {order.get('customer_email', '')}", style_body),
        Paragraph(f"Phone: {order.get('customer_phone', 'N/A')}", style_body),
    ]

    shipping_details = [
        Paragraph("SHIPPED TO (PHYSICAL DESTINATION)", style_section_title),
        Paragraph(f"<b>{ship_name}</b>", style_body_bold),
        Paragraph(f"{ship_line1}", style_body),
    ]
    if ship_line2:
        shipping_details.append(Paragraph(f"{ship_line2}", style_body))
    shipping_details.append(Paragraph(f"{ship_city}, {ship_state} {ship_zip}", style_body))
    shipping_details.append(Paragraph(f"{ship_country}", style_body))
    shipping_details.append(Paragraph(f"<b>Delivery Method:</b> {ship_method}", style_body))
    if tracking:
        shipping_details.append(Paragraph(f"<b>Carrier / Tracking:</b> {carrier or 'Courier'} #{tracking}", style_body))

    address_table = Table(
        [[customer_info, shipping_details]],
        colWidths=[3.6 * inch, 3.6 * inch]
    )
    address_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(address_table)

    story.append(Spacer(1, 16))

    # 3. Itemized Physical Products Table
    items_data = [
        [
            Paragraph("ITEM & SPECIFICATION", style_table_header),
            Paragraph("SKU", style_table_header),
            Paragraph("QTY", style_table_header),
            Paragraph("UNIT PRICE", style_table_header),
            Paragraph("TOTAL", ParagraphStyle("HdrRight", parent=style_table_header, alignment=2))
        ]
    ]

    for itm in items:
        title = itm.get("product_title", "Nyxeris Product")
        variant = itm.get("variant_title", "")
        if variant:
            title_text = f"<b>{title}</b><br/><font color='{text_muted}'>Variant: {variant}</font>"
        else:
            title_text = f"<b>{title}</b>"

        sku = itm.get("sku", "-")
        qty = str(itm.get("quantity", 1))
        unit_price = f"${itm.get('unit_price', 0.0):,.2f}"
        total_price = f"${itm.get('total_price', 0.0):,.2f}"

        items_data.append([
            Paragraph(title_text, style_table_cell),
            Paragraph(sku, style_table_cell),
            Paragraph(qty, style_table_cell),
            Paragraph(unit_price, style_table_cell),
            Paragraph(total_price, style_table_cell_right)
        ])

    items_table = Table(
        items_data,
        colWidths=[3.4 * inch, 1.2 * inch, 0.6 * inch, 1.0 * inch, 1.0 * inch]
    )
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, border_color),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, border_color),
    ]))
    story.append(items_table)

    story.append(Spacer(1, 12))

    # 4. Financial Summary Breakdown (Subtotal, Shipping, Tax, Total)
    subtotal = order.get("subtotal", 0.0)
    shipping_fee = order.get("shipping_fee", 0.0)
    tax = order.get("tax", 0.0)
    grand_total = order.get("total_amount", 0.0)

    ship_display = "FREE (Promotional)" if shipping_fee == 0 else f"${shipping_fee:,.2f}"

    packaging_tier = order.get("packaging_tier", "standard")
    packaging_fee = order.get("packaging_fee", 0.0)
    pkg_label = "Nyxeris Signature Box:" if packaging_tier == "premium" else "Packaging Standard:"
    pkg_display = f"${packaging_fee:,.2f}" if packaging_fee > 0 else "FREE (Included)"

    summary_data = [
        [Paragraph("Subtotal:", style_body), Paragraph(f"${subtotal:,.2f}", style_table_cell_right)],
        [Paragraph("Insured Physical Shipping:", style_body), Paragraph(ship_display, style_table_cell_right)],
        [Paragraph(pkg_label, style_body), Paragraph(pkg_display, style_table_cell_right)],
        [Paragraph("Estimated Sales Tax:", style_body), Paragraph(f"${tax:,.2f}", style_table_cell_right)],
        [
            Paragraph("<b>TOTAL PAID (USD):</b>", style_body_bold),
            Paragraph(f"<b>${grand_total:,.2f}</b>", ParagraphStyle("TotRight", parent=style_table_cell_right, fontName="Helvetica-Bold", fontSize=11, textColor=brand_primary))
        ]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[1.8 * inch, 1.2 * inch]
    )
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, 4), (-1, 4), 1, brand_accent),
    ]))

    # Right align the summary block
    wrapper_table = Table(
        [[Paragraph("<b>Payment Confirmation:</b> Paid in full via Card / Secure Checkout.<br/>Dispatched from Nyxeris Global Logistics Network.", style_tagline), summary_table]],
        colWidths=[4.2 * inch, 3.0 * inch]
    )
    wrapper_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(wrapper_table)

    story.append(Spacer(1, 24))

    # 5. Guarantee, Return Policy & Support Footer
    footer_elements = [
        HRFlowable(width="100%", thickness=0.8, color=border_color, spaceBefore=4, spaceAfter=8),
        Paragraph("<b>NYXERIS CUSTOMER PROMISE & GUARANTEE</b>", ParagraphStyle("FtrHdr", parent=style_tagline, fontName="Helvetica-Bold", textColor=brand_primary)),
        Paragraph("• 30-Day Transit & Quality Guarantee: Full replacement or refund for any items damaged in transit or defective upon arrival.", style_tagline),
        Paragraph("• 30-day no-hassle return policy on all eligible goods in original condition.", style_tagline),
        Paragraph(f"• If you have any questions regarding your parcel, tracking, or delivery, reply directly to this receipt or email <b>{settings.STORE_SUPPORT_EMAIL}</b>.", style_tagline),
        Spacer(1, 6),
        Paragraph(f"© {datetime.datetime.now().year} Nyxeris Ltd. All rights reserved. Registered for global logistics fulfillment.", ParagraphStyle("FtrCopy", parent=style_tagline, fontSize=7.5, textColor=text_muted))
    ]

    story.append(KeepTogether(footer_elements))

    # Build PDF
    doc.build(story)
    return str(pdf_path)


def generate_nyxeris_email_html(order: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """Generates a responsive, branded HTML email for order confirmation and receipt.
    Zero Whop branding - purely Nyxeris.
    """
    order_id = order["order_id"]
    cust_name = order.get("customer_name", "Valued Customer")
    total = f"${order.get('total_amount', 0.0):,.2f}"
    tracking = order.get("tracking_number", "")
    carrier = order.get("carrier", "")

    items_html = ""
    for itm in items:
        items_html += f"""
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid #e8e8e8; color: #1f1919; font-size: 13.5px;">
                <strong>{itm.get('product_title')}</strong>
                {f'<br/><span style="color: #767676; font-size: 12px;">Variant: {itm.get("variant_title")}</span>' if itm.get('variant_title') else ''}
            </td>
            <td style="padding: 12px 0; border-bottom: 1px solid #e8e8e8; color: #424242; font-size: 13.5px; text-align: center;">
                {itm.get('quantity')}
            </td>
            <td style="padding: 12px 0; border-bottom: 1px solid #e8e8e8; color: #1f1919; font-size: 13.5px; text-align: right; font-weight: 700;">
                ${itm.get('total_price', 0.0):,.2f}
            </td>
        </tr>
        """

    tracking_section = ""
    if tracking:
        tracking_section = f"""
        <div style="background: #edf4ed; border: 1px solid #b3ccb2; border-radius: 4px; padding: 14px; margin: 20px 0;">
            <p style="margin: 0; color: #324632; font-weight: bold; font-size: 12px; letter-spacing: 0.05em; text-transform: uppercase;">PARCEL DISPATCHED & TRACKED</p>
            <p style="margin: 4px 0 0; color: #1f1919; font-size: 13.5px;">Carrier: <strong>{carrier or 'Courier'}</strong> | Tracking: <strong>{tracking}</strong></p>
        </div>
        """

    pkg_fee = order.get("packaging_fee", 0.0)
    pkg_row = ""
    if pkg_fee > 0 or order.get("packaging_tier") == "premium":
        pkg_row = f"""
        <tr>
            <td style="color: #555555; font-size: 13.5px; padding: 6px 0;">Nyxeris Signature Box:</td>
            <td style="color: #1f1919; font-size: 13.5px; text-align: right; padding: 6px 0;">${pkg_fee if pkg_fee > 0 else 2.99:,.2f}</td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Order Confirmation - {order_id} | Nyxeris</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f7f5f4; font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1f1919;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f7f5f4; padding: 40px 15px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #e8e8e8; border-radius: 4px; padding: 36px; text-align: left; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);">
                        <tr>
                            <td>
                                <h1 style="margin: 0; color: #1f1919; font-family: 'Libre Baskerville', Georgia, serif; font-size: 24px; letter-spacing: 3px;">NYXERIS</h1>
                                <p style="margin: 6px 0 20px; color: #767676; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">Official Purchase Confirmation & Receipt</p>
                                <div style="height: 1px; background: #e8e8e8; margin-bottom: 24px;"></div>
                                
                                <p style="color: #1f1919; font-size: 15px; margin-bottom: 8px;">Hello <strong>{cust_name}</strong>,</p>
                                <p style="color: #555555; font-size: 13.5px; line-height: 1.6; margin-bottom: 20px;">
                                    Thank you for choosing Nyxeris. Your payment has been authorized and your curated items are being assembled at our logistics fulfillment hub.
                                </p>

                                <div style="background-color: #f7f5f4; border: 1px solid #e8e8e8; border-radius: 4px; padding: 16px; margin-bottom: 24px;">
                                    <p style="margin: 0; font-size: 11px; color: #767676; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">ORDER NUMBER</p>
                                    <p style="margin: 2px 0 12px; font-size: 15px; font-weight: bold; color: #1f1919; font-family: 'JetBrains Mono', monospace;">{order_id}</p>
                                    <p style="margin: 0; font-size: 11px; color: #767676; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">DESTINATION</p>
                                    <p style="margin: 2px 0 0; font-size: 13.5px; color: #424242; line-height: 1.4;">
                                        {order.get('shipping_address_line1')}, {order.get('shipping_city')}, {order.get('shipping_state')} {order.get('shipping_postal_code')}, {order.get('shipping_country')}
                                    </p>
                                </div>

                                {tracking_section}

                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                                    <thead>
                                        <tr>
                                            <th style="text-align: left; padding-bottom: 8px; color: #767676; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e8e8e8;">ITEM</th>
                                            <th style="text-align: center; padding-bottom: 8px; color: #767676; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e8e8e8;">QTY</th>
                                            <th style="text-align: right; padding-bottom: 8px; color: #767676; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #e8e8e8;">TOTAL</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {items_html}
                                    </tbody>
                                </table>

                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 10px; margin-bottom: 24px;">
                                    <tr>
                                        <td style="color: #555555; font-size: 13.5px; padding: 6px 0;">Subtotal:</td>
                                        <td style="color: #1f1919; font-size: 13.5px; text-align: right; padding: 6px 0;">${order.get('subtotal', 0.0):,.2f}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #555555; font-size: 13.5px; padding: 6px 0;">Insured Shipping:</td>
                                        <td style="color: #1f1919; font-size: 13.5px; text-align: right; padding: 6px 0;">${order.get('shipping_fee', 0.0):,.2f}</td>
                                    </tr>{pkg_row}
                                    <tr>
                                        <td style="color: #555555; font-size: 13.5px; padding: 6px 0;">Sales Tax:</td>
                                        <td style="color: #1f1919; font-size: 13.5px; text-align: right; padding: 6px 0;">${order.get('tax', 0.0):,.2f}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #1f1919; font-size: 15px; font-weight: 700; padding: 10px 0; border-top: 1px solid #1f1919;">Total Paid (USD):</td>
                                        <td style="color: #1f1919; font-size: 16px; font-weight: 700; text-align: right; padding: 10px 0; border-top: 1px solid #1f1919;">{total}</td>
                                    </tr>
                                </table>

                                <div style="text-align: center; margin: 30px 0;">
                                    <a href="{settings.BASE_URL}/order-confirmation/{order_id}" style="background-color: #324632; color: #ffffff; font-weight: 600; padding: 12px 28px; border-radius: 4px; text-decoration: none; display: inline-block; font-size: 13px; letter-spacing: 0.04em;">View Order & Download Official PDF Receipt</a>
                                </div>

                                <div style="font-size: 11.5px; color: #767676; border-top: 1px solid #e8e8e8; padding-top: 16px; line-height: 1.5;">
                                    <p style="margin: 0 0 6px;">Nyxeris Global Fulfillment Network | Customer Care: {settings.STORE_SUPPORT_EMAIL}</p>
                                    <p style="margin: 0;">30-Day Quality & Transit Guarantee applies to all customer shipments. Zero third-party branding.</p>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def send_nyxeris_receipt_email(order: Dict[str, Any], items: List[Dict[str, Any]], pdf_path: Optional[str] = None) -> bool:
    """Dispatches the white-labeled HTML receipt and attached PDF invoice to customer's Gmail.
    Supports standard SMTP / Gmail App Passwords if configured in .env.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    recipient = order.get("customer_email")
    if not recipient:
        return False

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    sender_email = os.getenv("SMTP_FROM", f"orders@{settings.STORE_NAME.lower()}.com")

    # If no SMTP server configured, log receipt readiness
    if not (smtp_host and smtp_user and smtp_pass):
        print(f"[Nyxeris Mailer] SMTP credentials not yet provided in .env. Email receipt ready for {recipient}. Preview at: {settings.BASE_URL}/api/orders/{order['order_id']}/email-preview")
        return False

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Official Order Confirmation & Receipt — {order['order_id']} | Nyxeris"
        msg["From"] = f"{settings.STORE_NAME} <{sender_email}>"
        msg["To"] = recipient

        # HTML body
        html_content = generate_nyxeris_email_html(order, items)
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Attach PDF invoice if generated
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header("Content-Disposition", "attachment", filename=f"Nyxeris_Receipt_{order['order_id']}.pdf")
                msg.attach(pdf_attachment)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print(f"[Nyxeris Mailer] Successfully dispatched receipt email to {recipient}")
        return True
    except Exception as err:
        print(f"[Nyxeris Mailer] Failed to send email to {recipient}: {err}")
        return False

