#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import re
from copy import deepcopy

from scrapy import Request, FormRequest
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import Spider

from bulkreefsupply.bulkreefsupply.config.env_config import EnvConfig
from bulkreefsupply.bulkreefsupply.config.user_agents import get_random_user_agent
from bulkreefsupply.bulkreefsupply.core.decorators import retry_invalid_response
from bulkreefsupply.bulkreefsupply.utils.clean_utils import clean
from bulkreefsupply.bulkreefsupply.utils.date_utils import get_today_date
from bulkreefsupply.bulkreefsupply.utils.file_utils import get_csv_records


class BulkReefSupplySpider(Spider):
    name = 'bulkreefsupply_spider'

    base_url = 'https://www.bulkreefsupply.com'
    add_to_cart_url = 'https://www.bulkreefsupply.com/checkout/cart/add'
    sitemap_url = "https://www.bulkreefsupply.com/sitemap/google_sitemap.xml"
    products_filename = f'{EnvConfig.PRODUCTS_FILE_DIR}/bulkreefsupply_products.csv'

    max_quantity = 1000

    start_urls = [
        sitemap_url,
    ]

    handle_httpstatus_list = [
        400, 401, 402, 403, 404, 405, 406, 407, 409,
        500, 501, 502, 503, 504, 505, 506, 507, 509,
    ]

    csv_columns = [
        'date', 'product_id', 'product_name', 'quantity', 'upc', 'vendor', 'sku', 'price', 'in_stock',
        'has_variants', 'product_url', 'main_image_url', 'secondary_image_urls', 'product_cart_id',
    ]

    feeds = {
        products_filename: {
            'format': 'csv',
            'encoding': 'utf8',
            'fields': csv_columns,
            'indent': 4,
            'overwrite': False
        }
    }

    custom_settings = {
        'FEEDS': feeds,
        'CONCURRENT_REQUESTS': 4,

        'SCRAPEOPS_API_KEY': EnvConfig.SCRAPEOPS_API_KEY,
        'SCRAPEOPS_PROXY_ENABLED': True,
        'SCRAPEOPS_PROXY_SETTINGS': {'country': 'us', 'keep_headers': True},

        "DOWNLOADER_MIDDLEWARES": {
            'scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk': 725,
        },
    }

    meta = {
        'handle_httpstatus_list': handle_httpstatus_list,
    }

    headers = {
        'authority': 'www.bulkreefsupply.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    }

    cart_req_form_data = {
        'product': '',  # product cart id like '14458'
        'form_key': 'ERVItuGv4aWQDJK1',
        'qty': '5',
    }

    cookies = {
        'form_key': 'ERVItuGv4aWQDJK1',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.seen_urls = []

    def start_requests(self):
        yield Request(self.base_url, callback=self.parse_input_product_urls, headers=self.headers)
        yield Request(self.sitemap_url, callback=self.parse_sitemap, headers=self.headers)

    @retry_invalid_response
    def parse_input_product_urls(self, response):
        urls = [rec['product_url'] for rec in get_csv_records('../input/input_product_urls.csv') if rec]
        return self.get_product_requests(response, urls)

    @retry_invalid_response
    def parse_sitemap(self, response):
        return self.get_product_requests(response, self.get_sitemap_urls(response))

    @retry_invalid_response
    def parse_details(self, response):
        try:
            item = response.meta['item']
            item.update(self.get_additional_details(response))
            item['date'] = get_today_date()
            item["weight"] = self.get_weight(response)
            item["dimensions"] = self.get_dimensions(response)
            item['main_image_url'] = self.get_main_image(response)
            item["secondary_image_urls"] = self.get_image_urls(response)
            item["product_url"] = response.url
            item['has_variants'] = False

            item['quantity'] = self.max_quantity // 2
            item['lower_limit'] = 0
            item['upper_limit'] = self.max_quantity

            prod = self.get_product_data(response)
            if 'children' in prod:
                item['has_variants'] = True

                for p in prod['children']:
                    try:
                        variant = deepcopy(item)
                        variant.update(self.get_product(p))
                        variant['product_cart_id'] = self.get_product_cart_id(response, sku=variant['product_id'])

                        if bool(variant['in_stock']):
                            self.append_cart_request(response, item=variant)
                        else:
                            variant["quantity"] = 0
                            yield variant
                    except Exception as variant_err:
                        self.logger.debug(f"Got Variant Error:\n{variant_err}")
            else:
                item.update(self.get_product(prod))
                item['product_cart_id'] = self.get_product_cart_id(response, sku=item['product_id'])

                if item['in_stock']:
                    self.append_cart_request(response, item=item)
                else:
                    item["quantity"] = 0
                    yield item

        except Exception as err:
            self.logger.debug(f"Got Error While Parsing Product {response.url}:\n {err}")

        yield from self.get_next_product_request(response)

    @retry_invalid_response
    def parse_quantity(self, response):
        self.set_limits(response)
        item = response.meta['item']

        try:
            if response.meta['item']['quantity'] < self.max_quantity and item['quantity'] != item['lower_limit']:
                yield self.get_add_to_cart_quantity_request(response)
            else:
                yield item
                yield from self.get_next_product_request(response)
        except Exception as err:
            print(f"Exception in parse_quantity: \n {err}")

    def get_sitemap_urls(self, response):
        urls = re.findall('<loc>(.*)</loc>', response.text)
        return list(set(url for url in urls if url and url.endswith('.html')))

    def get_product_data(self, response):
        return json.loads(response.css('[type="application/ld+json"]::text')[1].get())

    def get_product(self, prod):
        item = {}
        item['product_id'] = prod['productID']
        item["product_name"] = clean(prod['name'])
        item["vendor"] = clean(prod['brand']['name'])
        item["sku"] = prod['sku']
        item["price"] = prod['offers']['price']
        # item["description"] = clean(prod['description'])
        item['in_stock'] = 'instock' in prod['offers']['availability'].lower()
        return item

    def get_title(self, response):
        return clean(response.css('.product_title::text').get())

    def get_regular_price(self, response):
        return clean(response.css('.summary.entry-summary .price del bdi::text').get()) or self.get_sale_price(response)

    def get_sale_price(self, response):
        return clean(response.css('.summary.entry-summary .price bdi::text').getall()[-1])

    def get_image_urls(self, response):
        try:
            raw = [raw for raw in response.css('[type="text/x-magento-init"]::text').getall()
                   if 'mage/gallery/gallery' in raw and 'thumbs' in raw]

            raw = json.loads(raw[0])
            data = raw.get('[data-gallery-role=gallery-placeholder]', {}).get('mage/gallery/gallery', {}).get('data',
                                                                                                              {})
            return ", ".join([self.clean_image_url(r['thumb'][0]) for r in data])

        except Exception as image_err:
            print(image_err)

        return ", ".join([self.clean_image_url(response.css('::attr("data-product-image")').get())])

    def get_additional_details(self, response):
        details = {}

        for sel in response.css('#product-attribute-specs-table tbody tr'):
            if not (key := self.get_key(sel)):
                continue
            details[key] = clean(sel.css('td.col.data::text').get())

        return details

    def get_key(self, sel):
        return sel.css('th.col.label::text').get('').strip().replace(' ', '_').lower()

    def clean_image_url(self, url):
        code = re.findall(r'cache/(.*?)/', url)[0]
        return url.replace(f'/cache/{code}', '')

    def get_main_image(self, response):
        return self.clean_image_url(response.css('::attr("data-product-image")').get())

    def get_description_html(self, response):
        return response.css('#description').get()

    def get_dimensions(self, response):
        return clean(response.css('li:contains("Dimensions:") span::text').get()).replace('Dimensions:', '')

    def get_weight(self, response):
        return clean(response.css('li:contains("Weight:") span::text').get()).replace('Weight:', '')

    def get_product_cart_id(self, response, sku):
        return response.css(f'[data-product-sku="{sku}"]::attr(data-product-id)').get('')

    def set_limits(self, response):
        item = response.meta['item']

        if 'successfully added to cart.' in response.text.lower():
            response.meta['item']['lower_limit'] = item['quantity']
        else:
            response.meta['item']['upper_limit'] = item['quantity']

        response.meta['item']['quantity'] = self.get_limits_avg(item['upper_limit'], item['lower_limit'])

    def get_limits_avg(self, upper_limit, lower_limit):
        return (upper_limit + lower_limit) // 2

    def get_add_to_cart_quantity_request(self, response):
        return self.get_cart_request(response.meta['item'], response.meta)

    def append_cart_request(self, response, item):
        meta = deepcopy(self.meta)
        meta['item'] = item
        response.meta['product_requests'].insert(0, self.get_cart_request(item, meta))

    def get_cart_request(self, item, meta):
        req_headers = self.get_req_headers()
        req_headers['referer'] = item['product_url']

        form_data = deepcopy(self.cart_req_form_data)
        form_data['qty'] = str(item['quantity'])
        form_data['product'] = item['product_cart_id']

        return FormRequest(url=self.add_to_cart_url,
                           callback=self.parse_quantity,
                           formdata=form_data,
                           headers=req_headers,
                           cookies=self.cookies,
                           dont_filter=True,
                           meta=meta,
                           )

    def get_next_product_request(self, response, pop_limit=4):
        batch = []

        while pop_limit != 0:
            pop_limit -= 1

            if 'product_requests' in response.meta and response.meta['product_requests']:
                req = response.meta['product_requests'].pop(0)
                req.meta['product_requests'] = response.meta['product_requests']
                batch.append(req)

        return batch

    def get_product_requests(self, response, product_urls):
        for url in product_urls:
            url = url.rstrip('/')

            if not url or url.count('/') < 3 or not url.endswith('.html') or url in self.seen_urls:
                continue
            self.seen_urls.append(url)

            meta = deepcopy(self.meta)
            meta['item'] = {}

            req = Request(url, callback=self.parse_details, headers=self.get_req_headers(), meta=meta)
            response.meta.setdefault('product_requests', []).append(req)

        return self.get_next_product_request(response)

    def get_req_headers(self):
        headers = deepcopy(self.headers)
        headers['user-agent'] = get_random_user_agent()
        return headers


if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(BulkReefSupplySpider)
    process.start()
