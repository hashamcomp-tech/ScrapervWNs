import requests
from bs4 import BeautifulSoup
import unicodedata
import time
import os
import re
from ebooklib import epub
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

CHAPTERS_PER_VOLUME = 500

def normalize(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').lower()

def clean_text(text):
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if 'freewebnovel' not in normalize(l)]
    lines = [l for l in lines if 'webnovel' not in normalize(l)]
    lines = [l for l in lines if not (len(l) < 30 and '.com' in normalize(l))]
    merged = []
    for line in lines:
        if not line:
            merged.append('')
            continue
        if merged and merged[-1] and not merged[-1].endswith(('.', '!', '?', ':', '"', "'")) and line[0].islower():
            merged[-1] += ' ' + line
        else:
            merged.append(line)
    result = []
    prev_blank = False
    for line in merged:
        if not line:
            if not prev_blank:
                result.append('')
            prev_blank = True
        else:
            result.append(line)
            prev_blank = False
    return '\n\n'.join([l for l in result if l])

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

def scrape_chapter(args):
    i, url = args
    try:
        res = requests.get(url, headers=HEADERS)
        time.sleep(0.5)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.select_one('h2')
        title_text = title.get_text(strip=True) if title else f'Chapter {i}'
        content_div = soup.select_one('div.txt')
        if not content_div:
            return i, title_text, ''
        for tag in content_div.select('script, style, ins, iframe, h1, h2, h3'):
            tag.decompose()
        text = content_div.get_text(separator='\n')
        return i, title_text, clean_text(text)
    except Exception as e:
        print(f"  Error on chapter {i}: {e}")
        return i, f'Chapter {i}', ''

def make_epub(slug, novel_name, chapters_data, vol_num, start_ch, end_ch):
    book = epub.EpubBook()
    book.set_title(f"{novel_name} Vol.{vol_num}")
    book.set_language('en')
    chapters = []
    spine = ['nav']
    for i, title, content in chapters_data:
        if not content:
            continue
        c = epub.EpubHtml(title=title, file_name=f'chapter_{i}.xhtml', lang='en')
        html_content = f'<h1>{title}</h1>\n'
        for para in content.split('\n\n'):
            if para.strip():
                html_content += f'<p>{para.strip()}</p>\n'
        c.content = html_content
        book.add_item(c)
        chapters.append(c)
        spine.append(c)
    book.toc = chapters
    book.add_item(epub.EpubNcx())
    book.spine = spine
    os.makedirs('output', exist_ok=True)
    filepath = os.path.join('output', f"{slug}-vol{vol_num}-ch{start_ch}-{end_ch}.epub")
    epub.write_epub(filepath, book)
    print(f"Saved: {filepath}")

def scrape_novel(novel_url):
    slug = novel_url.rstrip('/').split('/')[-1]
    novel_name = slug.replace('-', ' ').title()
    print(f"Getting chapter count for: {novel_name}")
    total = get_total_chapters(novel_url)
    if not total:
        print("Could not determine chapter count.")
        return
    print(f"Found {total} chapters. Starting scrape...")
    volumes = []
    for start in range(1, total + 1, CHAPTERS_PER_VOLUME):
        end = min(start + CHAPTERS_PER_VOLUME - 1, total)
        volumes.append((start, end))
    for vol_num, (start, end) in enumerate(volumes, 1):
        print(f"\nVolume {vol_num}: chapters {start}-{end}")
        tasks = [(i, f"{novel_url}/chapter-{i}") for i in range(start, end + 1)]
        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(scrape_chapter, task): task for task in tasks}
            for future in as_completed(futures):
                i, title, content = future.result()
                results[i] = (title, content)
                print(f"  Chapter {i}/{total}")
        chapters_data = []
        for i in range(start, end + 1):
            title, content = results.get(i, (f'Chapter {i}', ''))
            chapters_data.append((i, title, content))
        make_epub(slug, novel_name, chapters_data, vol_num, start, end)
        time.sleep(2)
    print(f"\nAll volumes saved to output/")

NOVELS = [
    "https://freewebnovel.com/novel/reverend-insanity",
]

if __name__ == "__main__":
    for url in NOVELS:
        scrape_novel(url)
        time.sleep(3)
