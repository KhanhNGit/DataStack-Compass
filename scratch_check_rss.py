import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

blogs = [
  {"name": "Towards Data Science", "url": "https://towardsdatascience.com"},
  {"name": "KDnuggets", "url": "https://www.kdnuggets.com"},
  {"name": "Analytics Vidhya", "url": "https://www.analyticsvidhya.com/blog"},
  {"name": "Data Science Central", "url": "https://www.datasciencecentral.com"},
  {"name": "Kaggle Blog (No Free Hunch)", "url": "https://blog.kaggle.com"},
  {"name": "365 Data Science Blog", "url": "https://365datascience.com/trending"},
  {"name": "DataCamp Blog", "url": "https://www.datacamp.com/blog"},
  {"name": "Dataconomy", "url": "https://dataconomy.com"},
  {"name": "Datanami", "url": "https://www.datanami.com"},
  {"name": "insideBIGDATA", "url": "https://insidebigdata.com"},
  {"name": "Databricks Blog", "url": "https://www.databricks.com/blog"},
  {"name": "Cloudera Blog", "url": "https://blog.cloudera.com"},
  {"name": "AWS Big Data Blog", "url": "https://aws.amazon.com/blogs/big-data"},
  {"name": "Google Cloud Blog — Data & AI", "url": "https://cloud.google.com/blog/products/data-analytics"},
  {"name": "Microsoft Azure Data Blog", "url": "https://techcommunity.microsoft.com/category/azure/blog/microsoftdatablog"},
  {"name": "Snowflake Blog", "url": "https://www.snowflake.com/blog"},
  {"name": "Confluent Blog", "url": "https://www.confluent.io/blog"},
  {"name": "dbt Labs Blog", "url": "https://www.getdbt.com/blog"},
  {"name": "Airflow Blog (Apache)", "url": "https://airflow.apache.org/blog"},
  {"name": "Dataiku Blog", "url": "https://blog.dataiku.com"},
  {"name": "Hevo Data Blog", "url": "https://hevodata.com/blog"},
  {"name": "Fivetran Blog", "url": "https://www.fivetran.com/blog"},
  {"name": "Oracle AI & Data Science Blog", "url": "https://blogs.oracle.com/ai-and-datascience"},
  {"name": "SAS Subconscious Musings", "url": "https://blogs.sas.com/content/subconsciousmusings"},
  {"name": "Databricks Engineering Blog", "url": "https://engineering.databricks.com"},
  {"name": "Airbnb Data Blog", "url": "https://medium.com/airbnb-engineering/tagged/data"},
  {"name": "Netflix Tech Blog — Data", "url": "https://netflixtechblog.com/tagged/data-engineering"},
  {"name": "Uber Engineering Blog", "url": "https://www.uber.com/en-US/blog/engineering"},
  {"name": "LinkedIn Engineering — Data", "url": "https://engineering.linkedin.com/blog/topic/data"},
  {"name": "Stitch Fix Tech Blog", "url": "https://multithreaded.stitchfix.com/blog"},
  {"name": "Smart Data Collective", "url": "https://www.smartdatacollective.com"},
  {"name": "DataFloq", "url": "https://datafloq.com/read"},
  {"name": "Planet Big Data", "url": "https://planetbigdata.com"},
  {"name": "NYC Data Science Academy Blog", "url": "https://nycdatascience.com/blog"},
  {"name": "Data Science Association Blog", "url": "http://www.datascienceassn.org/blog"},
  {"name": "Becoming a Data Scientist", "url": "https://www.becomingadatascientist.com/category/blog"},
  {"name": "Simply Statistics", "url": "https://simplystatistics.org"},
  {"name": "Andrew Gelman (Statistical Modeling)", "url": "https://statmodeling.stat.columbia.edu"},
  {"name": "FlowingData", "url": "https://flowingdata.com"},
  {"name": "FiveThirtyEight (now ABC)", "url": "https://fivethirtyeight.com"},
  {"name": "Freakonometrics", "url": "https://freakonometrics.hypotheses.org"},
  {"name": "Variance Explained", "url": "https://varianceexplained.org"},
  {"name": "Julia Silge Blog", "url": "https://juliasilge.com/blog"},
  {"name": "Junk Charts", "url": "https://junkcharts.typepad.com"},
  {"name": "Chris Albon", "url": "https://chrisalbon.com"},
  {"name": "Towards AI Blog", "url": "https://towardsai.net/p"},
  {"name": "Machine Learning Mastery", "url": "https://machinelearningmastery.com/blog"},
  {"name": "What's The Big Data?", "url": "https://whatsthebigdata.com"},
  {"name": "Data Science 101", "url": "https://101.datascience.community"},
  {"name": "Occam's Razor", "url": "https://www.kaushik.net/avinash"},
  {"name": "Simo Ahava's Blog", "url": "https://www.simoahava.com"},
  {"name": "Data 36", "url": "https://data36.com"},
  {"name": "Statistical Thinking", "url": "https://www.fharrell.com"},
  {"name": "SSP.sh (Simon Späti)", "url": "https://www.ssp.sh"},
  {"name": "Confessions of a Data Guy", "url": "https://www.confessionsofadataguy.com"},
  {"name": "Bernard Marr Blog", "url": "https://bernardmarr.com/blog"},
  {"name": "DataExpert.io Newsletter", "url": "https://blog.dataexpert.io"},
  {"name": "Practical Data Engineering", "url": "https://www.pracdata.io"},
  {"name": "Data Engineering Central", "url": "https://dataengineeringcentral.substack.com"},
  {"name": "Data Engineer Things", "url": "https://dataengineerthings.substack.com"},
  {"name": "Data Engineering Community Digest", "url": "https://dataengineeringcommunity.substack.com"},
  {"name": "SeattleDataGuy Newsletter", "url": "https://seattledataguy.substack.com"},
  {"name": "The Analytics Engineering Roundup", "url": "https://roundup.getdbt.com"},
  {"name": "IBM Data & AI Blog", "url": "https://www.ibm.com/blog/data-and-ai"},
  {"name": "O'Reilly Data Science Topics", "url": "https://www.oreilly.com/radar/topics/data"},
  {"name": "Womeninbigdata.org Blog", "url": "https://www.womeninbigdata.org/blog"},
  {"name": "XenonStack Big Data Blog", "url": "https://www.xenonstack.com/blog/tag/big-data-engineering"},
]

def check_rss(blog):
    url = blog['url']
    possible_rss_urls = [
        url.rstrip('/') + '/feed',
        url.rstrip('/') + '/rss',
        url.rstrip('/') + '/rss.xml',
        url.rstrip('/') + '/feed.xml',
        url.rstrip('/') + '/index.xml',
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        rss_match = re.search(r'<link[^>]*type=["\']application/rss\+xml["\'][^>]*href=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
        if not rss_match:
            rss_match = re.search(r'<link[^>]*href=["\']([^"\']+)["\'][^>]*type=["\']application/rss\+xml["\']', r.text, re.IGNORECASE)
            
        atom_match = re.search(r'<link[^>]*type=["\']application/atom\+xml["\'][^>]*href=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
        if not atom_match:
            atom_match = re.search(r'<link[^>]*href=["\']([^"\']+)["\'][^>]*type=["\']application/atom\+xml["\']', r.text, re.IGNORECASE)
            
        if rss_match:
            href = rss_match.group(1)
            if not href.startswith('http'):
                href = url.rstrip('/') + ('/' if not href.startswith('/') else '') + href
            return {'name': blog['name'], 'url': url, 'rss': href, 'status': 'Found Meta RSS'}
            
        if atom_match:
            href = atom_match.group(1)
            if not href.startswith('http'):
                href = url.rstrip('/') + ('/' if not href.startswith('/') else '') + href
            return {'name': blog['name'], 'url': url, 'rss': href, 'status': 'Found Meta Atom'}
    except Exception as e:
        pass
    
    for purl in possible_rss_urls:
        try:
            r = requests.get(purl, headers=headers, timeout=5)
            if r.status_code == 200 and ('xml' in r.headers.get('Content-Type', '').lower() or 'rss' in r.text[:200].lower()):
                return {'name': blog['name'], 'url': url, 'rss': purl, 'status': 'Guessed RSS'}
        except Exception:
            continue
            
    return {'name': blog['name'], 'url': url, 'rss': None, 'status': 'No RSS Found'}

def main():
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_rss, blog): blog for blog in blogs}
        for future in as_completed(futures):
            results.append(future.result())
            
    found = [r for r in results if r['rss']]
    not_found = [r for r in results if not r['rss']]
    
    with open('rss_results.json', 'w', encoding='utf-8') as f:
        json.dump({'total': len(blogs), 'found': len(found), 'not_found': len(not_found), 'found_list': found, 'not_found_list': not_found}, f, indent=2, ensure_ascii=False)
    print(f"Total: {len(blogs)}, Found RSS: {len(found)}, Not Found: {len(not_found)}")

if __name__ == '__main__':
    main()
