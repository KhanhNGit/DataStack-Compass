# src/reporter/pdf_generator.py
import textwrap
from jinja2 import Template
from weasyprint import HTML
import logging

logger = logging.getLogger(__name__)

class PDFReporter:
    def __init__(self):
        self.template_str = textwrap.dedent("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @page { margin: 2cm; }
                body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.5; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #2980b9; margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 5px;}
                h3 { color: #e67e22; margin-top: 25px; font-size: 1.3em; }
                .summary-box { background: #ecf0f1; padding: 15px; border-left: 5px solid #3498db; border-radius: 4px; margin-bottom: 20px;}
                .risk-High { color: #e74c3c; font-weight: bold; }
                .risk-Medium { color: #f39c12; font-weight: bold; }
                .risk-Low { color: #27ae60; font-weight: bold; }
                
                /* CSS mới để mix Text và Table mượt mà */
                .list-item { display: list-item; margin-left: 20px; margin-bottom: 6px; font-size: 0.95em; }
                .sub-header { font-weight: bold; color: #34495e; margin-top: 15px; margin-bottom: 5px; font-size: 1.1em; border-bottom: 1px dashed #ccc; }
                
                /* CSS cho Bảng nâng cấp thư viện */
                .upgrade-table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 15px; font-size: 0.85em; }
                .upgrade-table th, .upgrade-table td { border: 1px solid #bdc3c7; padding: 8px; text-align: left; }
                .upgrade-table th { background-color: #ecf0f1; color: #2c3e50; font-weight: bold; }
                
                .footer { margin-top: 50px; font-size: 0.8em; color: #7f8c8d; text-align: center; border-top: 1px solid #bdc3c7; padding-top: 10px;}
            </style>
        </head>
        <body>
            <h1>OSS Release Analysis: {{ source_name | replace('_', ' ') | title }}</h1>
            
            <div class="summary-box">
                <h2>Executive Summary</h2>
                <p><strong>Target Version:</strong> {{ latest }}</p>
                <p><strong>Previous Version:</strong> {{ previous }}</p>
                <p><strong>Risk Level:</strong> <span class="risk-{{ analysis.risk_level }}">{{ analysis.risk_level }}</span></p>
                <p><strong>Impact:</strong> {{ analysis.upgrade_impact }}</p>
                <p><strong>Recommendation:</strong> {{ analysis.recommendation }}</p>
            </div>

            <h2>Release Details & Module Updates</h2>
            {% for category, items in notes.items() %}
                <h3>{{ category }}</h3>
                <div class="category-content">
                {% for item in items %}
                    {# Kiểm tra nếu item là chuỗi text thông thường #}
                    {% if item is string %}
                        {% if item.startswith('🔹') %}
                            <div class="sub-header">{{ item | replace('🔹 ', '') }}</div>
                        {% else %}
                            <div class="list-item">{{ item }}</div>
                        {% endif %}
                    
                    {# Kiểm tra nếu item là một Dictionary chứa dữ liệu Bảng #}
                    {% elif item is mapping and item.type == 'table' %}
                        <table class="upgrade-table">
                            <thead>
                                <tr>
                                    <th>{{ item.data[0][0] }}</th>
                                    <th>{{ item.data[0][1] }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in item.data[1:] %}
                                <tr>
                                    <td>{{ row[0] }}</td>
                                    <td>{{ row[1] }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% endif %}
                {% endfor %}
                </div>
            {% endfor %}

            <div class="footer">
                <p>Generated automatically by OSS Release Analyzer | Source: <a href="{{ url }}">{{ url }}</a></p>
            </div>
        </body>
        </html>
        """)

    def generate(self, source_name: str, url: str, latest: str, previous: str, 
                 notes: dict, analysis: dict[str, str], output_path: str) -> None:
        try:
            logger.info(f"Generating PDF report for {source_name} at {output_path}")
            template = Template(self.template_str)
            html_content = template.render(
                source_name=source_name, url=url, latest=latest, 
                previous=previous, notes=notes, analysis=analysis
            )
            HTML(string=html_content).write_pdf(output_path)
            logger.info("PDF generation successful.")
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise