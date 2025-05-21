import scrapy
import urllib.parse

class EpicGamesSpider(scrapy.Spider):
    name = "epicgames"
    allowed_domains = ["store.epicgames.com"]
    
    def __init__(self, product_name=None, *args, **kwargs):
        super(EpicGamesSpider, self).__init__(*args, **kwargs)
        self.product_name = product_name
        if product_name:
            # Construct the search URL for Epic Games
            # This URL might need adjustment based on actual Epic Games search page structure
            encoded_product_name = urllib.parse.quote_plus(product_name)
            self.start_urls = [f"https://store.epicgames.com/ru/browse?q={encoded_product_name}"]
        else:
            # Fallback or handle required product_name
            self.start_urls = ["https://store.epicgames.com/ru/"] # Default or error page
            # raise ValueError("product_name argument is required")

    def parse(self, response):
        # This parsing logic is a best guess and likely needs significant adjustment
        # based on the actual HTML structure of Epic Games search results.
        
        # Example: find game cards (selector might be wrong)
        for game_card in response.css('div.css-xxxxxx'): # Replace with actual game card selector
            title = game_card.css('div.css-yyyyyy::text').get() # Replace with actual title selector
            price = game_card.css('span.css-zzzzzz::text').get() # Replace with actual price selector
            url = game_card.css('a::attr(href)').get() # Replace with actual link selector

            if title and price and url:
                 # Ensure URL is absolute
                 absolute_url = response.urljoin(url)
                 yield {
                    'title': title.strip(),
                    'current_price': price.strip(), # You might need more complex price cleaning
                    'original_price': None, # Epic Games structure might differ for original/discounted prices
                    'url': absolute_url,
                 }

        # Basic pagination (selector likely needs adjustment)
        next_page = response.css('a.css-next-page-button::attr(href)').get() # Replace with actual next page selector
        if next_page:
            absolute_next_page = response.urljoin(next_page)
            yield response.follow(absolute_next_page, self.parse) 