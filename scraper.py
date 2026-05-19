import requests
from bs4 import BeautifulSoup
import time
import os
import re
from ebooklib import epub

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def clean_text(text):
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    return '\n\n'.join(lines)

def get_total_chapters(novel_url):
    res = requests.get(novel_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
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
    content_div = soup.select_one('div.txt')
    if not content_div:
        return title_text, ''
    for tag in content_div.select('script, style, ins, iframe'):
        tag.decompose()
    text = content_div.get_text(separator='\n')
    return title_text, clean_text(text)

def scrape_novel(novel_url):
    slug = novel_url.rstrip('/').split('/')[-1]
    novel_name = slug.replace('-', ' ').title()
    print(f"Getting chapter count for: {novel_name}")
    total = get_total_chapters(novel_url)
    if not total:
        print("Could not determine chapter count.")
        return
    print(f"Found {total} chapters. Starting scrape...")

    book = epub.EpubBook()
    book.set_title(novel_name)
    book.set_language('en')

    chapters = []
    spine = ['nav']
    os.makedirs('output', exist_ok=True)

    for i in range(1, total + 1):
        url = f"{novel_url}/chapter-{i}"
        print(f"Chapter {i}/{total}: {url}")
        try:
            title, content = scrape_chapter(url)
            if not content:
                continue
            c = epub.EpubHtml(title=title, file_name=f'chapter_{i}.xhtml', lang='en')
            html_content = f'<h1>{title}</h1>'
            for para in content.split('\n\n'):
                if para.strip():
                    html_content += f'<p>{para.strip()}</p>'
            c.content = html_content
            book.add_item(c)
            chapters.append(c)
            spine.append(c)
            time.sleep(1.5)
        except Exception as e:
            print(f"  Error: {e}")
            continue

    book.toc = chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    filepath = os.path.join('output', f"{slug}.epub")
    epub.write_epub(filepath, book)
    print(f"\nDone! Saved to: {filepath}")

NOVELS = [
    "https://freewebnovel.com/novel/mother-of-learning",
]

if __name__ == "__main__":
    for url in NOVELS:
        scrape_novel(url)
        time.sleep(3)
