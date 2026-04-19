import sys
import os
sys.path.insert(0, os.path.abspath("."))

import logging
from scraper.crawler import RecursiveCrawler, CrawlConfig

# Configure logging to see progress
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def main():
    print("Testing RecursiveCrawler...")
    
    # Configure for a small test: depth 1, max 2 pages
    config = CrawlConfig(max_depth=1, max_pages=2)
    crawler = RecursiveCrawler(config)
    
    # Start crawling from Xtrim as an example
    seed_urls = ["https://www.xtrim.com.ec/"]
    results = crawler.crawl(seed_urls)
    
    print(f"\nCrawl completed. Visited {len(results)} pages.")
    for i, res in enumerate(results):
        print(f"Page {i+1}: {res.url} (Length: {len(res.html)} bytes)")
        
    print("\nCheck 'data/raw/current/' to see the saved HTML snapshots.")

if __name__ == "__main__":
    main()
