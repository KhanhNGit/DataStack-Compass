import os
import json
from jinja2 import Environment, FileSystemLoader

def generate_preview():
    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('tech_blog_digest.html.j2')
    
    # Load sample data
    sample_file = 'reports/blog/summary/kaggle_blog_no_free_hunch_summary.json'
    posts = []
    if os.path.exists(sample_file):
        with open(sample_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
            
    # Render template
    html_output = template.render(
        date_range="22/07 - 29/07/2026",
        posts=posts
    )
    
    # Save output
    output_path = 'reports/blog/preview_digest.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
        
    print(f"Preview generated at {output_path}")

if __name__ == "__main__":
    generate_preview()
