import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from typing import List, Dict
import schedule
import time
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

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
                continue

        return papers

    def scrape_biorxiv(self, url: str) -> List[Dict]:
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        papers = []

        for article in soup.find_all('article', class_='article-item'):
            try:
                title = article.find('a', class_='highwire-cite-linked-title').text.strip()
                abstract = article.find('div', class_='abstract').text.strip()
                date = article.find('span', class_='article-date').text.strip()
                article_url = "https://www.biorxiv.org" + article.find('a', class_='highwire-cite-linked-title')['href']
                
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'date': date,
                    'source': 'bioRxiv',
                    'url': article_url
                })
            except AttributeError:
                continue

        return papers

    def scrape_medrxiv(self, url: str) -> List[Dict]:
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        papers = []

        for article in soup.find_all('div', class_='article-item'):
            try:
                title = article.find('a', class_='article-title').text.strip()
                abstract = article.find('div', class_='abstract-text').text.strip()
                date = article.find('span', class_='pub-date').text.strip()
                article_url = "https://www.medrxiv.org" + article.find('a', class_='article-title')['href']
                
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'date': date,
                    'source': 'medRxiv',
                    'url': article_url
                })
            except AttributeError:
                continue

        return papers

    def scrape_sciencedirect(self, url: str) -> List[Dict]:
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        papers = []

        for article in soup.find_all('li', class_='ResultItem'):
            try:
                title = article.find('h2').text.strip()
                abstract = article.find('div', class_='abstract').text.strip()
                date = article.find('span', class_='publication-date').text.strip()
                article_url = article.find('h2').find('a')['href']
                if not article_url.startswith('http'):
                    article_url = 'https://www.sciencedirect.com' + article_url
                
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'date': date,
                    'source': 'ScienceDirect',
                    'url': article_url
                })
            except AttributeError:
                continue

        return papers

    def scrape_who_trials(self, url: str) -> List[Dict]:
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        papers = []

        for trial in soup.find_all('tr', class_='trial-record'):
            try:
                title = trial.find('td', class_='trial-title').text.strip()
                abstract = trial.find('td', class_='trial-description').text.strip()
                date = trial.find('td', class_='trial-date').text.strip()
                trial_url = "https://trialsearch.who.int" + trial.find('a')['href']
                
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'date': date,
                    'source': 'WHO Clinical Trials',
                    'url': trial_url
                })
            except AttributeError:
                continue

        return papers

    def scrape_europe_pmc(self, url: str) -> List[Dict]:
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        papers = []

        for article in soup.find_all('div', class_='citation'):
            try:
                title = article.find('h3', class_='title').text.strip()
                abstract = article.find('p', class_='abstract').text.strip()
                date = article.find('span', class_='publication-date').text.strip()
                article_url = "https://europepmc.org" + article.find('a', class_='title-link')['href']
                
                papers.append({
                    'title': title,
                    'abstract': abstract,
                    'date': date,
                    'source': 'Europe PMC',
                    'url': article_url
                })
            except AttributeError:
                continue

        return papers

    def run_scraper(self) -> List[Dict]:
        all_papers = []
        
        source_methods = {
            'pubmed': self.scrape_pubmed,
            'biorxiv': self.scrape_biorxiv,
            'medrxiv': self.scrape_medrxiv,
            'sciencedirect': self.scrape_sciencedirect,
            'who': self.scrape_who_trials,
            'europepmc': self.scrape_europe_pmc
        }

        for source in self.sources:
            for source_key, scrape_method in source_methods.items():
                if source_key in source.lower():
                    try:
                        papers = scrape_method(source)
                        all_papers.extend(papers)
                        print(f"Successfully scraped {len(papers)} papers from {source_key}")
                    except Exception as e:
                        print(f"Error scraping {source_key}: {str(e)}")
                    break
        
        # Create backup directory if it doesn't exist
        backup_dir = os.getenv('BACKUP_DIR', './paper_backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Save to JSON for backup
        backup_file = os.path.join(backup_dir, f'papers_{datetime.now().strftime("%Y%m%d")}.json')
        with open(backup_file, 'w') as f:
            json.dump(all_papers, f)
            
        return all_papers