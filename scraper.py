import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from typing import List, Dict
import schedule
import time
import os
from dotenv import load_dotenv

load_dotenv()

class MedicalPaperScraper:
    def __init__(self, sources: List[str]):
        self.sources = sources
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape_pubmed(self, url: str) -> List[Dict]:
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        papers = []

        for article in soup.find_all('article', class_='full-docsum'):
            try:
                title = article.find('a', class_='docsum-title').text.strip()
                abstract = article.find('div', class_='full-view-snippet').text.strip()
                date = article.find('span', class_='docsum-journal-citation').text.strip()
                
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'date': date,
                    'source': 'PubMed',
                    'url': url
                })
            except AttributeError:
                continue  # Skip articles with missing information

        return papers

    def run_scraper(self) -> List[Dict]:
        all_papers = []
        for source in self.sources:
            if 'pubmed' in source.lower():
                papers = self.scrape_pubmed(source)
                all_papers.extend(papers)
        
        # Create backup directory if it doesn't exist
        backup_dir = os.getenv('BACKUP_DIR', './paper_backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Save to JSON for backup
        backup_file = os.path.join(backup_dir, f'papers_{datetime.now().strftime("%Y%m%d")}.json')
        with open(backup_file, 'w') as f:
            json.dump(all_papers, f)
            
        return all_papers