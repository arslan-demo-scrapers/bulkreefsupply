import time


def retry_invalid_response(callback):
    def wrapper(spider, response):
        if response.status >= 400:
            if response.status == 404:
                spider.logger.info('Page not found.')

                # If Sitemap URL is not working the extract product links by crawling categories pages.
                if spider.sitemap_url in response.url:
                    return spider.get_categories_requests()

                return spider.get_next_product_request(response)

            retry_times = response.meta.get('retry_times', 0)
            if retry_times < 3:
                time.sleep(2)
                response.meta['retry_times'] = retry_times + 1
                return response.request.replace(dont_filter=True, meta=response.meta)

            spider.logger.info("Dropped after 3 retries. url: {}".format(response.url))
            response.meta.pop('retry_times', None)
            return spider.get_next_product_request(response)

        return callback(spider, response)

    return wrapper
