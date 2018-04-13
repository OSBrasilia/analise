#!/usr/bin/env python3

from bs4 import BeautifulSoup
from datetime import datetime
import urllib.request
import re
import shutil
import os
import textract
from pathlib import Path

def download_as(url, filepath):
    """Fetches a single page and saves it."""
    if filepath.exists():
        print('>> Replacing file %s from "%s"' % (filepath, url))
    else:
        print('>> New file %s from "%s"' % (filepath, url))
    with urllib.request.urlopen(url) as response:
        with filepath.open('wb') as dest:
            shutil.copyfileobj(response, dest)


def fetch_page(url):
    """Fetches a single page and parses it."""
    print('Fetching', url)
    with urllib.request.urlopen(url) as response:
        html = response.read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def crawl_category(cat_url, entry_finder, next_finder=None):
    """Crawls all URLs from a start page, looking for additional pages.
    Fetches the page at cat_url and tries to look for entries in it using entry_finder.
    Then uses next_finder to find the URL for the next page of items, and keeps looking
    for entries until no next page is available.
    Args:
        cat_url (str): the URL to fetch
        entry_finder (function): takes the BeautifulSoup object and returns an array of anchors.
        next_finder (function): takes the BeautifulSoup object and returns a single anchor.
    Returns:
        urls (list): the list of all URLs found by entry_finder.
    """

    urls = set()
    page_url = cat_url
    while page_url:
        soup = fetch_page(page_url)
        entries = [a['href'] for a in entry_finder(soup)]
        next_link = None if next_finder is None else next_finder(soup)
        if next_link is None or 'href' not in next_link.attrs:
            next_url = None
        else:
            next_url = next_link['href']
        print('Crawled', page_url, ': ', len(entries), 'entries. Next: ', next_url)
        urls = urls.union(entries)
        page_url = next_url
    return urls

def crawl_verba():
    """Crawls all verba files."""
    root = fetch_page('http://www.cl.df.gov.br/web/guest/quadro-demonstrativo-verba-indenizatoria')
    path = Path('files/verba')
    if not path.is_dir():
        path.mkdir(parents=True)

    elements = root.select('.results-row a[href*="document_library_display"]')
    years = set(((e.get_text().strip(), e['href']) for e in elements))
    for year, url in years:
        print('\t>>%s: "%s"' % (year, url))
        year_soup = fetch_page(url)
        for entry in year_soup.select('a[href*=verba]'):
            if year in entry.get_text() and year != entry.get_text().strip():
                filename = path / entry.get_text().strip()
                filename = filename.with_suffix('.pdf')
                entry_soup = fetch_page(entry['href'])
                entry = entry_soup.select_one('.lfr-asset-name a[href]')
                if entry is not None:
                    download_as(entry['href'], filename)


if __name__ == '__main__':
    crawl_verba()
