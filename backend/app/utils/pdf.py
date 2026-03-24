import os
import pdfkit
from jinja2 import Template

INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Invoice {{ invoice.number }}</title>
    <style>
        body { font-family: 'Helvetica Neue', 'Helvetica', sans-serif; padding: 40px; color: #333; }
        .invoice-box { max-width: 800px; margin: auto; padding: 30px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0, 0, 0, .15); }
        .header { display: flex; justify-content: space-between; margin-bottom: 40px; }
        .header-left { float: left; }
        .header-right { float: right; text-align: right; }
        .title { font-size: 36px; line-height: 45px; color: #333; }
        .details { margin-top: 20px; clear: both; margin-bottom: 40px; }
        .client-info { float: left; }
        .invoice-info { float: right; text-align: right; }
        table { width: 100%; line-height: inherit; text-align: left; border-collapse: collapse; clear: both; margin-bottom: 40px; }
        table th { background: #eee; border-bottom: 1px solid #ddd; font-weight: bold; padding: 10px; }
        table td { padding: 10px; border-bottom: 1px solid #eee; }
        .totals { float: right; width: 300px; }
        .totals-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee; }
        .totals-row.bold { font-weight: bold; font-size: 1.1em; border-top: 2px solid #333; border-bottom: none; padding-top: 10px; }
        .footer { text-align: center; margin-top: 50px; font-size: 0.85em; color: #777; border-top: 1px solid #eee; padding-top: 20px; clear:both;}
    </style>
</head>
<body>
    <div class="invoice-box">
        <div class="header">
            <div class="header-left">
                <h2 style="margin:0;">{{ company.name }}</h2>
                <p style="margin:0; font-size:0.9em; color:#555;">ICE: {{ company.ice }} | IF: {{ company.tax_id }}</p>
                <p style="margin:0; font-size:0.9em; color:#555;">RC: {{ company.rc }}</p>
            </div>
            <div class="header-right">
                <div class="title">FACTURE</div>
                <div style="font-size:1.2em; font-weight:bold; margin-top:5px;">N° {{ invoice.number }}</div>
            </div>
        </div>
        
        <div class="details">
            <div class="client-info">
                <strong>Facturé à:</strong><br>
                {{ client.name }}<br>
                ICE: {{ client.ice }}<br>
                {{ client.address }}<br>
            </div>
            <div class="invoice-info">
                <strong>Date de Facture:</strong> {{ invoice.date }}<br>
                <strong>Date d'Échéance:</strong> {{ invoice.due_date if invoice.due_date else 'A réception' }}<br>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Description</th>
                    <th style="text-align:center;">Qté</th>
                    <th style="text-align:right;">P.U (HT)</th>
                    <th style="text-align:right;">TVA</th>
                    <th style="text-align:right;">Total HT</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td>{{ item.product_name }}</td>
                    <td style="text-align:center;">{{ item.quantity }}</td>
                    <td style="text-align:right;">{{ "{:,.2f}".format(item.unit_price) }} MAD</td>
                    <td style="text-align:right;">{{ item.vat_rate }}%</td>
                    <td style="text-align:right;">{{ "{:,.2f}".format(item.quantity * item.unit_price) }} MAD</td>
                </tr>
                {% endendfor %}
            </tbody>
        </table>
        
        <div class="totals">
            <div class="totals-row">
                <span>Total HT:</span>
                <span>{{ "{:,.2f}".format(invoice.total_excl_tax) }} MAD</span>
            </div>
            <div class="totals-row">
                <span>Total TVA:</span>
                <span>{{ "{:,.2f}".format(invoice.vat_amount) }} MAD</span>
            </div>
            <div class="totals-row bold">
                <span>Total TTC:</span>
                <span>{{ "{:,.2f}".format(invoice.total_incl_tax) }} MAD</span>
            </div>
        </div>
        
        <div class="footer">
            {{ company.name }} - ICE: {{ company.ice }} - IF: {{ company.tax_id }}<br>
            {{ company.address }}
        </div>
    </div>
</body>
</html>
"""

def generate_invoice_pdf(invoice, items, company, client) -> bytes:
    """
    Generates a PDF from the HTML invoice template.
    Returns the PDF file as bytes.
    """
    template = Template(INVOICE_TEMPLATE)
    
    # Process items to include names
    formatted_items = []
    for item in items:
        # In MVP we might not have the product eagerly loaded
        product_name = item.product.name if hasattr(item, 'product') and item.product else f"Produit/Service #{item.product_id}"
        formatted_items.append({
            "product_name": product_name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "vat_rate": item.vat_rate
        })
        
    html_content = template.render(
        invoice=invoice,
        items=formatted_items,
        company=company,
        client=client
    )
    
    # Generate PDF safely
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'disable-smart-shrinking': '',
    }
    
    # Windows fallback if wkhtmltopdf is not strictly available locally during direct execution
    # In docker, it will use the wrapper installed in the apt-get step
    try:
        pdf_bytes = pdfkit.from_string(html_content, False, options=options)
        return pdf_bytes
    except Exception as e:
        # Fallback to HTML bytes if wkhtmltopdf fails locally
        print(f"PDFKit failed: {e}. Falling back to HTML string bytes.")
        return html_content.encode('utf-8')
