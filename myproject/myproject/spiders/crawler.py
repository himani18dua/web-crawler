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

class FindBrokenSpider(scrapy.Spider):
    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': headers(),
        'ROBOTSTXT_OBEY': False,
        'RETRY_TIMES': 1,
        'LOG_LEVEL': 'INFO',  # Adjust log level as needed
    }
    name = "crawler"
    handle_httpstatus_list = [i for i in range(400, 600)]

    def __init__(self, url=None, *args, **kwargs):
        super(FindBrokenSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url] if url else []
        self.start_page = url
        self.broken_links = []
        self.visited_urls = set()
        self.logger.info(f'Initialized with start URL: {self.start_page}')

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(FindBrokenSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):
        if not self.start_urls:
            self.logger.error("No start URL provided")
            return
        for url in self.start_urls:
            if not is_valid_url(url):
                self.logger.error(f"Invalid URL: {url}")
                self.broken_links.append({
                    "Source_Page": "NA",
                    "Link_Text": "NA",
                    "Broken_Page_Link": url,
                    "HTTP_Code": "Invalid URL",
                    "External": "NA"
                })
                continue
            self.visited_urls.add(url)
            yield scrapy.Request(url, callback=self.parse, errback=self.handle_error, meta={'is_external': False, 'source': url})

    def parse(self, response):
        is_external = response.meta.get('is_external', False)
        source_page = response.meta.get('source', '')
        # selector = Selector(response)

# Find the link element using its URL
        # link_element = selector.xpath(f"//a[@href='{response.url}']")

# Extract the link text if the element is found
        link_text = response.meta.get('text')
        

        if response.status in self.handle_httpstatus_list:
            self.log_broken_link(response.url, source_page, link_text, response.status, is_external)
            return

        content_type = response.headers.get("content-type", "").lower()
        self.logger.debug(f'Content type of {response.url} is {content_type}')
        
        if b'text' not in content_type:
            self.logger.info(f'{response.url} is NOT HTML')
            return

        for a in response.xpath('//a[@href]'):
            link_text = a.xpath('string(.)').get().strip()
            link = response.urljoin(a.xpath('./@href').get())
            if not is_valid_url(link):
                continue

            link_is_external = not self.follow_this_domain(link, self.start_page)
            if link_is_external:
                if not is_external:  # Only log broken external links if they were originally internal
                    yield scrapy.Request(link, callback=self.check_external_link, errback=self.handle_error, meta={'source': response.url, 'text': link_text})
            else:
                if link not in self.visited_urls:
                    self.visited_urls.add(link)
                    yield scrapy.Request(link, callback=self.parse, errback=self.handle_error, meta={'source': response.url, 'text': link_text})

    def check_external_link(self, response):
        is_external = True
        source_page = response.meta.get('source', '')
        if response.status in self.handle_httpstatus_list:
            self.log_broken_link(response.url, source_page, response.meta['text'], response.status, is_external)

    def handle_error(self, failure):
        self.logger.error(repr(failure))
        request = failure.request
        self.logger.error(f'Unhandled error on {request.url}')
        self.log_broken_link(request.url, 'Unknown', None, failure.value.response.status if failure.value.response else 'DNSLookupError or other unhandled', False)

    def log_broken_link(self, url, source, text, status, is_external):
        item = {
            "Source_Page": source,
            "Link_Text": text,
            "Broken_Page_Link": url,
            "HTTP_Code": status,
            "External": is_external
        }
        self.broken_links.append(item)
        self.logger.info(f'Logged broken link: {item}')

    def follow_this_domain(self, link, start_page):
        return urlparse(link.strip()).netloc == urlparse(start_page).netloc

    def spider_closed(self, spider):
        output_dir = 'output_directory'
        if not self.broken_links:
            self.broken_links.append({
                "Source_Page": "NA",
                "Link_Text": "NA",
                "Broken_Page_Link": "No broken links found",
                "HTTP_Code": "200",
                "External": "NA"
            })
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(os.path.join(output_dir, 'broken_links.json'), 'w') as f:
            json.dump(self.broken_links, f, indent=4)

if __name__ == '__main__':
    run_spider(FindBrokenSpider)
