# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from itemadapter import ItemAdapter
from marketplace.models import Product, Market, Offer # Импортируйте ваши модели Django

class MarketParserPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        product_id = adapter.get('product_id')
        market_id = adapter.get('market_id')

        if not product_id or not market_id:
            # Если нет product_id или market_id, пропускаем элемент
            spider.logger.warning(f"Skipping item, missing product_id or market_id: {item}")
            return item # Или можно выбросить DropItem

        try:
            product = Product.objects.get(pk=product_id)
            market = Market.objects.get(pk=market_id)
        except (Product.DoesNotExist, Market.DoesNotExist):
            spider.logger.warning(f"Skipping item, Product or Market not found for item: {item}")
            return item # Пропускаем, если продукт или маркет не найдены

        # Получаем или создаем предложение
        offer_url = adapter.get('url')
        if not offer_url:
             spider.logger.warning(f"Skipping item, missing URL: {item}")
             return item
             
        offer_defaults = {
            'price': adapter.get('current_price'),
            'original_price': adapter.get('original_price'),
            # Добавьте другие поля предложения, если они есть в item
        }
        
        offer, created = Offer.objects.get_or_create(
            product=product,
            market=market,
            url=offer_url,
            defaults=offer_defaults
        )
        
        # Если предложение уже существует, обновляем цену, если она изменилась
        if not created and offer.price != adapter.get('current_price'):
             offer.price = adapter.get('current_price')
             offer.original_price = adapter.get('original_price')
             # Обновите другие поля, если необходимо
             offer.save()
             spider.logger.info(f"Updated existing offer: {offer.url}")
        elif created:
             spider.logger.info(f"Created new offer: {offer.url}")

        # Вы можете добавить здесь очистку и валидацию данных перед сохранением
        # Например:
        # if adapter.get('price') is not None:
        #     offer.price = float(adapter['price'])
        # else:
        #     offer.price = 0.0 # Установите значение по умолчанию или пропустите

        return item
