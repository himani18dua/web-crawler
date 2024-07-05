import json
import os
from scrapy import Selector
from urllib.parse import urlparse

import scrapy
from scrapy import signals
from scraper_helper import headers, run_spider

def is_valid_url(url):
    try:
        result = urlparse(url.strip())
        return result.scheme in ['http', 'https'] and bool(result.netloc)
    except Exception as e:
        return False

class FindImagesWithoutAltSpider(scrapy.Spider):
    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': headers(),
        'ROBOTSTXT_OBEY': False,
        'RETRY_TIMES': 1,
        'LOG_LEVEL': 'INFO',  # Adjust log level as needed
    }
    name = "image_crawler"
    handle_httpstatus_list = [i for i in range(400, 600)]

    def __init__(self, url=None, *args, **kwargs):
        super(FindImagesWithoutAltSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url] if url else []
        self.start_page = url
        self.images_without_alt = []
        self.visited_urls = set()
        self.logger.info(f'Initialized with start URL: {self.start_page}')

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(FindImagesWithoutAltSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):
        if not self.start_urls:
            self.logger.error("No start URL provided")
            return
        for url in self.start_urls:
            if not is_valid_url(url):
                self.logger.error(f"Invalid URL: {url}")
                continue
            self.visited_urls.add(url)
            yield scrapy.Request(url, callback=self.parse, errback=self.handle_error, meta={'is_external': False, 'source': url})

    def parse(self, response):
        is_external = response.meta.get('is_external', False)
        source_page = response.meta.get('source', '')

        if response.status in self.handle_httpstatus_list:
            self.logger.error(f"Failed to fetch {response.url} with status {response.status}")
            return

        content_type = response.headers.get("content-type", "").lower()
        self.logger.debug(f'Content type of {response.url} is {content_type}')
        
        if b'text' not in content_type:
            self.logger.info(f'{response.url} is NOT HTML')
            return

        # Check images without alt text only if the page is internal or the start page
        if not is_external:
            self.check_images_without_alt(response)

        for a in response.xpath('//a[@href]'):
            link_text = a.xpath('string(.)').get().strip()
            link = response.urljoin(a.xpath('./@href').get())
            if not is_valid_url(link):
                continue

            link_is_external = not self.follow_this_domain(link, self.start_page)
            if not link_is_external and link not in self.visited_urls:
                self.visited_urls.add(link)
                yield scrapy.Request(link, callback=self.parse, errback=self.handle_error, meta={'source': response.url, 'text': link_text, 'is_external': link_is_external})

    def check_images_without_alt(self, response):
        images = response.xpath('//img')
        for img in images:
            alt_text = img.xpath('@alt').get()
            if not alt_text:
                img_url = response.urljoin(img.xpath('@src').get())
                self.images_without_alt.append({
                    'source_page': response.url,
                    'image_url': img_url
                })

    def handle_error(self, failure):
        self.logger.error(repr(failure))
        request = failure.request
        self.logger.error(f'Unhandled error on {request.url}')

    def follow_this_domain(self, link, start_page):
        return urlparse(link.strip()).netloc == urlparse(start_page).netloc

    def spider_closed(self, spider):
        output_dir = 'output_directory'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not self.images_without_alt:
            self.images_without_alt.append({
                "source_page": "NA",
                "image_url": "No images without alt text found"
            })
        with open(os.path.join(output_dir, 'images_without_alt.json'), 'w') as f:
            json.dump(self.images_without_alt, f, indent=4)

if __name__ == '__main__':
    run_spider(FindImagesWithoutAltSpider)
