#!/usr/bin/env python3
"""
PDF Report Generator for ZOBON Trust Score Monitoring System
Generates comprehensive PDF reports with charts and analytics
"""

import sys
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
import pandas as pd
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.db_writer import db_manager

class ZobonReportGenerator:
    def __init__(self):
        self.report_data = {}
        self.charts = {}

    def fetch_report_data(self, days=30, brand=None):
        """Fetch data for report generation"""
        print(f"Fetching report data for last {days} days...")

        try:
            conn = db_manager.connection_pool.getconn()
            cursor = conn.cursor()

            where_conditions = ["timestamp >= NOW() - INTERVAL '%s days'"]
            params = [days]

            if brand:
                where_conditions.append("brand = %s")
                params.append(brand)

            where_clause = " AND ".join(where_conditions)

            cursor.execute(f"""
                SELECT COUNT(*) as total_records,
                       AVG(trust_score),
                       MIN(trust_score),
                       MAX(trust_score),
                       COUNT(CASE WHEN sentiment > 0.2 THEN 1 END) AS pos,
                       COUNT(CASE WHEN sentiment < -0.2 THEN 1 END) AS neg,
                       COUNT(CASE WHEN sentiment BETWEEN -0.2 AND 0.2 THEN 1 END) AS neu
                FROM campaign_scores
                WHERE {where_clause}
            """, params)

            row = cursor.fetchone()
            self.report_data = {
                "total": row[0],
                "avg_trust": round(row[1], 2) if row[1] else 0,
                "min_trust": row[2],
                "max_trust": row[3],
                "positive": row[4],
                "negative": row[5],
                "neutral": row[6]
            }

            cursor.execute(f"""
                SELECT timestamp::date, AVG(trust_score)
                FROM campaign_scores
                WHERE {where_clause}
                GROUP BY timestamp::date
                ORDER BY timestamp::date
            """, params)

            trend_data = cursor.fetchall()
            self.report_data["trend_df"] = pd.DataFrame(trend_data, columns=["Date", "Trust Score"])

        except Exception as e:
            print(f"Error fetching report data: {e}")
            raise
        finally:
            db_manager.connection_pool.putconn(conn)

    def generate_chart(self):
        df = self.report_data.get("trend_df")
        if df is None or df.empty:
            return None

        fig, ax = plt.subplots(figsize=(8, 4))
        sns.lineplot(data=df, x="Date", y="Trust Score", marker="o", ax=ax)
        ax.set_title("Trust Score Trend")
        ax.set_ylabel("Trust Score")
        ax.set_xlabel("Date")
        ax.grid(True)

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)
        return buf

    def generate_pdf(self, output_file, brand=None):
        print("Generating PDF Report...")
        pdf = SimpleDocTemplate(output_file, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='CenterTitle', alignment=1, fontSize=16, spaceAfter=12))

        elements.append(Paragraph("ZOBON Trust Score Monitoring Report", styles['CenterTitle']))
        if brand:
            elements.append(Paragraph(f"Brand: <b>{brand}</b>", styles['Normal']))
        elements.append(Spacer(1, 12))

        if not self.report_data or self.report_data.get("total", 0) == 0:
            elements.append(Paragraph("<b>No data available.</b>", styles['Normal']))
        else:
            stats = self.report_data
            table_data = [
                ["Total Mentions", stats["total"]],
                ["Average Trust Score", stats["avg_trust"]],
                ["Min Trust Score", stats["min_trust"]],
                ["Max Trust Score", stats["max_trust"]],
                ["Positive Mentions", stats["positive"]],
                ["Negative Mentions", stats["negative"]],
                ["Neutral Mentions", stats["neutral"]]
            ]

            table = Table(table_data, colWidths=[200, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

            chart_buf = self.generate_chart()
            if chart_buf:
                img = Image(chart_buf, width=6*inch, height=3*inch)
                elements.append(img)

        elements.append(Spacer(1, 24))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))

        pdf.build(elements)
        print(f"PDF report saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", help="Brand name (optional)")
    parser.add_argument("--output", help="Output PDF filename", default="zobon_report.pdf")
    parser.add_argument("--days", help="Number of days to include", type=int, default=30)
    args = parser.parse_args()

    generator = ZobonReportGenerator()
    generator.fetch_report_data(days=args.days, brand=args.brand)
    generator.generate_pdf(args.output, brand=args.brand)
