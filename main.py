from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup
import requests
import pandas as pd
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)

def tables_to_csv(dfs):
    buffer = BytesIO()

    first = True
    for i, df in enumerate(dfs, start=1):
        if not first:
            # 2 empty rows
            buffer.write(b"\n\n")
        first = False

        # Table title
        buffer.write(f"Table {i}\n".encode())

        # Table data
        df.to_csv(buffer, index=False)

    buffer.seek(0)
    return buffer
def tables_to_pdf(dfs):
    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    page_width, _ = A4
    usable_width = page_width - pdf.leftMargin - pdf.rightMargin

    for i, df in enumerate(dfs, start=1):
        # Heading
        elements.append(Paragraph(f"<b>Table {i}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        # Table data
        data = [df.columns.tolist()] + df.values.tolist()
        col_widths = [usable_width / len(df.columns)] * len(df.columns)

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 30))

    pdf.build(elements)
    buffer.seek(0)
    return buffer


# -------------------------------------------------
# ROUTE
# -------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        tag_name = request.form.get("tag")
        output = request.form.get("output_format")
        try:
            response = requests.get(url, timeout=5)
        except requests.RequestException:
            return "No internet connection or URL not reachable"
        soup = BeautifulSoup(response.content, "lxml")

        elements = soup.find_all(tag_name)

        if not elements:
            return "No matching tags found on this page"

        if tag_name == "table":
            dfs = []
            for table in elements:
                df = pd.read_html(str(table))[0]
                dfs.append(df)
            if output == "csv":
                csv_buffer = tables_to_csv(dfs)
                return send_file(
                    csv_buffer,
                    as_attachment=True,
                    download_name="tables_separate.csv",
                    mimetype="text/csv"
                )
            elif output == "excel":
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    for i, df in enumerate(dfs, start=1):
                        df.to_excel(writer, sheet_name=f"Table_{i}", index=False)
                buffer.seek(0)

                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name="tables_separate.xlsx"
                )
            elif output == "pdf":
                pdf_buffer = tables_to_pdf(dfs)
                return send_file(
                    pdf_buffer,
                    as_attachment=True,
                    download_name="tables_separate.pdf",
                    mimetype="application/pdf"
                )
        result = "\n\n".join([el.get_text(strip=True) for el in elements])
        return result

    return render_template("index.html")


if __name__ == "__main__":
    app.run(port=3010)


