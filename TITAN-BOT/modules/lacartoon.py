import datetime
import json
import re
from bs4 import BeautifulSoup
from requests import Session
import lxml.html
from lxml.html import fromstring

class Cartoons:
    def __init__(self):
        self.base_url = 'https://lacartoons.com'
        self.scraper = Session()
        agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0'
        self.scraper.headers['User-Agent'] = agent
        self.scraper.headers['referer'] = self.base_url

    def get_series_links(self, page=1):
        url = f"{self.base_url}/?page={page}"
        response = self.scraper.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        series_links = []
        series_div = soup.find_all('a', href=True)
        for serie in series_div:
            if '/serie/' in serie['href']:
                full_url = f"{self.base_url}{serie['href']}"
                series_links.append(full_url)
        return series_links

    def get_all_pages(self):
        url = self.base_url
        response = self.scraper.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        pagination = soup.find('ul', class_='pagination')
        last_page = 1
        if pagination:
            last_page_link = pagination.find_all('a', href=True)[-2]  # Penúltima página es la última numerada
            last_page = int(re.search(r'page=(\d+)', last_page_link['href']).group(1))
        return last_page

    def get_series_details(self, series_url):
        response = self.scraper.get(series_url)
        tree = fromstring(response.content)
        title_element = tree.xpath('//h2[contains(@class, "subtitulo-serie-seccion")]/text()')
        title = title_element[0].strip() if title_element else None
        episodes_count_element = tree.xpath('//p[contains(text(), "Episodios:")]/span/text()')
        episodes_count = episodes_count_element[0].strip() if episodes_count_element else None
        language_element = tree.xpath('//p[contains(text(), "Idioma:")]/span/text()')
        language = language_element[0].strip() if language_element else None
        year_element = tree.xpath('//span[@class="marcador marcador-año"]/text()')
        year = year_element[0].strip() if year_element else None
        rating_element = tree.xpath('//span[@class="valoracion1"]/text()')
        rating = rating_element[0].strip() if rating_element else None
        review_element = tree.xpath('//p[contains(text(), "Reseña:")]/span/text()')
        review = review_element[0].strip() if review_element else None
        image_element = tree.xpath('//div[@class="imagen-serie"]//img/@src')
        image = f"{self.base_url}{image_element[0]}" if image_element else None
        episodes = self.get_episodes(tree)
        
        return {
            'title': title,
            'episodes_count': episodes_count,
            'language': language,
            'year': year,
            'rating': rating,
            'review': review,
            'image': image,
            'episodes': episodes,
            'url': series_url
        }

    def get_episodes(self, tree):
        episodes = []
        
        # Intentar múltiples formas de encontrar episodios
        episode_selectors = [
            '//div[contains(@class, "contenedor-episondios")]//li//a',
            '//div[@class="contenedor-episondios"]//li//a',
            '//div[contains(@class, "episodios")]//li//a',
            '//a[contains(@class, "episodio")]'
        ]
        
        for selector in episode_selectors:
            episode_links = tree.xpath(selector)            
            if episode_links:
                for episode in episode_links:                    
                    link = f"{self.base_url}{episode.get('href')}" if episode.get('href') else None
                    title = None
                    if episode.text:
                        title = episode.text.strip()
                    elif episode.xpath('text()'):
                        title = episode.xpath('text()')[0].strip()
                    if not title:
                        title_elements = episode.xpath('text()')
                        title = ' '.join(title_elements) if title_elements else "No Title"
                    iframe_src = self.get_chapter_iframe(link) if link else None
                
                    episodes.append({
                        'link': link,
                        'title': title,
                        'iframe': iframe_src
                    })
                if episodes:
                    break        
        return episodes

    def get_chapter_iframe(self, chapter_url):
        try:
            response = self.scraper.get(chapter_url)
            tree = fromstring(response.content)
            iframe = tree.xpath('//iframe/@src')
            return iframe[0] if iframe else None
        except Exception:
            return None

    def scrape_all_series(self):
        last_page = self.get_all_pages()
        all_series_links = []
        for page in range(1, last_page + 1):
            print(f"Scraping page {page}...")
            links = self.get_series_links(page)
            all_series_links.extend(links)
        all_series_details = []
        for link in all_series_links:
            print(f"Scraping series details from {link}...")
            details = self.get_series_details(link)
            all_series_details.append(details)
        return all_series_details