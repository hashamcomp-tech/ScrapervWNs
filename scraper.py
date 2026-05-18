import requests
from bs4 import BeautifulSoup
import time
import os
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://freewebnovel.com',
}

def clean_text(text):
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    return '\n\n'.join(lines)

def get_total_chapters(novel_url):
    """Get total chapter count from novel page metadata."""
    res = requests.get(novel_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Try og:novel:lastest_chapter_url meta tag
    meta = soup.find('meta', property='og:novel:lastest_chapter_url')
    if meta:
        url = meta.get('content', '')
        match = re.search(r'chapter-(\d+)', url)
        if match:
            return int(match.group(1))
    return None

def scrape_chapter(url):
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    title = soup.select_one('h2, h1')
    title_text = title.get_text(strip=True) if title else url.split('/')[-1]
    
    # This site puts content in div.txt
    content_div = soup.select_one('div.txt')
    if not content_div:
        return title_text, '[Content not found]'
    
    for tag in content_div.select('script, style, ins, iframe'):
        tag.decompose()
    
    text = content_div.get_text(separator='\n')
    return title_text, clean_text(text)

def scrape_novel(novel_url):
    """Scrape an entire novel and save to .txt."""
    slug = novel_url.rstrip('/').split('/')[-1]
    novel_name = slug.replace('-', ' ').title()
    
    print(f"Getting chapter count for: {novel_name}")
    total = get_total_chapters(novel_url)
    
    if not total:
        print("Could not determine chapter count.")
        return
    
    print(f"Found {total} chapters. Starting scrape...")
    
    os.makedirs('output', exist_ok=True)
    filepath = os.path.join('output', f"{slug}.txt")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"{novel_name}\n{'='*60}\n\n")
        
        for i in range(1, total + 1):
            url = f"{novel_url}/chapter-{i}"
            print(f"Chapter {i}/{total}: {url}")
            try:
                title, content = scrape_chapter(url)
                f.write(f"\n{'='*60}\n{title}\n{'='*60}\n\n")
                f.write(content + '\n')
                time.sleep(1.5)
            except Exception as e:
                print(f"  Error: {e}")
                continue
    
    print(f"\nDone! Saved to: {filepath}")

# ── Add your novels here ──────────────────────────────────────
NOVELS = [
    "https://freewebnovel.com/novel/shadow-slave",
]

if __name__ == "__main__":
    for url in NOVELS:
        scrape_novel(url)
        time.sleep(3)
