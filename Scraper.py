import requests
from bs4 import BeautifulSoup
import time
import os
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def clean_text(text):
    # Remove extra whitespace and blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    return '\n\n'.join(lines)

def get_chapter_links(novel_url):
    """Get all chapter URLs from a novel's page."""
    print(f"Fetching chapter list from: {novel_url}")
    res = requests.get(novel_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    links = []
    for a in soup.select('ul.chapter-list a, .wp-manga-chapter a'):
        href = a.get('href', '')
        if '/chapter-' in href:
            links.append(href if href.startswith('http') else 'https://freewebnovel.com' + href)
    
    # Sort chapters in order
    links = sorted(set(links), key=lambda u: int(re.search(r'chapter-(\d+)', u).group(1)))
    print(f"Found {len(links)} chapters.")
    return links

def scrape_chapter(url):
    """Scrape text content from a single chapter."""
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Get chapter title
    title = soup.select_one('h1, .chapter-title, .entry-title')
    title_text = title.get_text(strip=True) if title else url.split('/')[-1]
    
    # Get chapter content — remove scripts, ads, comments
    content_div = soup.select_one('.chapter-content, #chapter-content, .text-left')
    if not content_div:
        return title_text, ''
    
    # Remove unwanted tags
    for tag in content_div.select('script, style, .ads, .comment, ins, iframe'):
        tag.decompose()
    
    text = content_div.get_text(separator='\n')
    return title_text, clean_text(text)

def scrape_novel(novel_url):
    """Scrape an entire novel and save to .txt."""
    # Get novel title from URL slug
    slug = novel_url.rstrip('/').split('/')[-1]
    novel_name = slug.replace('-', ' ').title()
    filename = f"{slug}.txt"
    
    chapter_urls = get_chapter_links(novel_url)
    if not chapter_urls:
        print("No chapters found. Check the URL.")
        return
    
    os.makedirs('output', exist_ok=True)
    filepath = os.path.join('output', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"{novel_name}\n{'='*60}\n\n")
        
        for i, url in enumerate(chapter_urls, 1):
            print(f"Scraping chapter {i}/{len(chapter_urls)}: {url}")
            try:
                title, content = scrape_chapter(url)
                f.write(f"\n{'='*60}\n{title}\n{'='*60}\n\n")
                f.write(content + '\n')
                time.sleep(1.5)  # polite delay
            except Exception as e:
                print(f"  Error on {url}: {e}")
                continue
    
    print(f"\nDone! Saved to: {filepath}")

# ── Add your novels here ──────────────────────────────────────
NOVELS = [
    "https://freewebnovel.com/novel/shadow-slave",
    # "https://freewebnovel.com/novel/another-novel-here",
]

if __name__ == "__main__":
    for url in NOVELS:
        scrape_novel(url)
        time.sleep(3)
