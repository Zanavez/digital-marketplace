import scrapy
import urllib.parse
import re
import json
import logging
from scrapy.utils.project import get_project_settings


class SteamSpider(scrapy.Spider):
    name = "steam"
    allowed_domains = ["store.steampowered.com", "api.steampowered.com"]
    
    def __init__(self, product_name=None, product_id=None, market_id=None, *args, **kwargs):
        super(SteamSpider, self).__init__(*args, **kwargs)
        self.product_name = product_name
        self.product_id = product_id
        self.market_id = market_id
        settings = get_project_settings()
        self.api_key = settings.get('STEAM_API_KEY')
        self.logger.setLevel(logging.DEBUG)
        
        if product_name:
            encoded_product_name = urllib.parse.quote_plus(product_name)
            self.start_urls = [f"https://store.steampowered.com/search/?term={encoded_product_name}"]
        else:
            self.start_urls = ["https://store.steampowered.com/"]

    def parse(self, response):
        for game in response.css('a.search_result_row'):
            try:
                url = game.css('::attr(href)').get()
                app_id = None
                if url:
                    app_id_match = re.search(r'/app/(\d+)/?', url)
                    if app_id_match:
                        app_id = app_id_match.group(1)
                
                if not app_id:
                    continue

                title_element = game.css('span.title::text').get()
                title = title_element.strip() if title_element else None

                price_container = game.css('div.search_price')
                current_price_cleaned = None
                original_price_cleaned = None

                if price_container:
                    current_price_element = price_container.css('div.discount_final_price::text').get()
                    if not current_price_element:
                        current_price_element = price_container.css('div.search_price::text').get()
                    if not current_price_element:
                        current_price_element = price_container.css('div.col.search_price.responsive_secondrow::text').get()

                    if current_price_element:
                        current_price_cleaned = re.sub(r'[^\d,.]', '', current_price_element).replace(',', '.')
                        try:
                            current_price_cleaned = float(current_price_cleaned) if current_price_cleaned else None
                        except ValueError:
                            current_price_cleaned = None

                    original_price_element = price_container.css('span.discount_original_price::text').get()
                    if original_price_element:
                        original_price_cleaned = re.sub(r'[^\d,.]', '', original_price_element).replace(',', '.')
                        try:
                            original_price_cleaned = float(original_price_cleaned) if original_price_cleaned else None
                        except ValueError:
                            original_price_cleaned = None

                meta_data = {
                    'title': title,
                    'current_price': current_price_cleaned,
                    'original_price': original_price_cleaned,
                    'url': url,
                    'product_id': self.product_id,
                    'market_id': self.market_id
                }

                if app_id and self.api_key:
                    api_url = f"https://api.steampowered.com/ISteamApps/GetAppDetails/v2/?appids={app_id}&key={self.api_key}"
                    yield scrapy.Request(
                        api_url,
                        callback=self.parse_api_response,
                        meta=meta_data
                    )
                else:
                    if title and url:
                        item = {
                            'title': title,
                            'current_price': current_price_cleaned,
                            'original_price': original_price_cleaned,
                            'url': url,
                            'product_id': self.product_id,
                            'market_id': self.market_id
                        }
                        yield item

            except Exception as e:
                self.logger.error(f"Error processing game item: {str(e)}")

        next_page_link = response.css('div.search_pagination a:contains("Next")::attr(href)').get() or \
                         response.css('div.search_pagination a[rel="next"]::attr(href)').get()

        if next_page_link:
            absolute_next_page = response.urljoin(next_page_link)
            yield response.follow(absolute_next_page, self.parse, meta={'product_id': self.product_id, 'market_id': self.market_id})

    def parse_api_response(self, response):
        try:
            data = json.loads(response.text)
            app_id = list(data.keys())[0]
            app_data = data[app_id].get('data', {})
            
            description = app_data.get('short_description', '')
            release_date = app_data.get('release_date', {}).get('date', '')
            developer = app_data.get('developers', [''])[0]
            publisher = app_data.get('publishers', [''])[0]
            
            yield {
                'title': response.meta.get('title'),
                'current_price': response.meta.get('current_price'),
                'original_price': response.meta.get('original_price'),
                'url': response.meta.get('url'),
                'description': description,
                'release_date': release_date,
                'developer': developer,
                'publisher': publisher,
                'product_id': response.meta.get('product_id'),
                'market_id': response.meta.get('market_id')
            }
        except Exception as e:
            self.logger.error(f"Error parsing API response: {str(e)}")
            yield {
                'title': response.meta.get('title'),
                'current_price': response.meta.get('current_price'),
                'original_price': response.meta.get('original_price'),
                'url': response.meta.get('url'),
                'product_id': response.meta.get('product_id'),
                'market_id': response.meta.get('market_id')
            }
