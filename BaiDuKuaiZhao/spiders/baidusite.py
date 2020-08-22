# -*- coding: utf-8 -*-

import time
import scrapy
import os
import re
from scrapy import Selector
from urllib.parse import urlparse, urljoin
from copy import deepcopy
from multiprocessing import Manager


class BaiDuSiteSpider(scrapy.Spider):
    name = 'baidusite'
    regex = re.compile("[\/\\\:\*\?\"\<\>\|]")
    file_list = []

    def __init__(self, url_domain, save_dir, Q=None):
        super(BaiDuSiteSpider, self).__init__()
        self.url_domain = url_domain
        self.save_dir = save_dir
        self.url_head = f'http://{url_domain}'
        self.Q = Q if Q else Manager().Queue()
        self.Q.put('开始处理数据')

    def makedir_folder(self, source_path):
        if not os.path.exists(source_path):
            os.makedirs(source_path)

    def is_exist(self, file_path_name):
        if not os.path.exists(file_path_name):
            return True
        return False

    def err_callback_1(self, error):
        pass

    def get_new_sources(self, sources, url_layer):
        dont_filter = False
        if not sources:
            return None, None, None, None, None
        elif sources.startswith("http"):
            resources_url = sources
            dont_filter = True
        elif sources.startswith('//'):
            resources_url = f"http:{sources}"
            dont_filter = True
        elif sources.startswith('/'):
            resources_url = urljoin(self.url_head, sources.replace('/', '', 1))
        elif sources.startswith("../"):
            resources_url = urljoin(self.url_head, sources.replace('../', ''))
        elif sources.startswith("./"):
            resources_url = urljoin(self.url_head, sources.replace('./', ''))
        elif sources.endswith(".png") or sources.endswith(".jpg") or sources.endswith(".jpeg") or sources.endswith(
                ".css") or sources.endswith(".js"):
            resources_url = urljoin(self.url_head, sources)
        else:
            return None, None, None, None, None

        sources_urlparse_path = urlparse(resources_url).path
        sources_path = os.path.dirname(sources_urlparse_path).replace('/', '', 1)
        sources_name = os.path.basename(sources_urlparse_path)
        if not sources_name:
            sources_name = str(int(time.time()))
        sources_name = self.regex.sub("", sources_name)

        new_sources_path = os.path.join(self.save_dir, sources_path)
        new_sources_path_name = os.path.join(new_sources_path, sources_name)
        relative_path = os.path.join(sources_path, sources_name)
        relative_path = f"{''.join(['../' for i in range(url_layer)])}{relative_path}"

        resources_url = resources_url.replace('\\', '/')

        return resources_url, new_sources_path, new_sources_path_name, relative_path, dont_filter

    def start_requests(self):
        for root, dirs, files in os.walk(self.save_dir):
            for file in files:
                if file.endswith(".html"):
                    self.file_list.append(os.path.join(root, file))

        for file in self.file_list:
            file_path = file.split(self.save_dir)[1]
            dirname = os.path.dirname(file_path)
            if dirname == '\\':
                url_layer = 0
            else:
                url_layer = dirname.count("\\")

            with open(file, "r", encoding="utf-8") as f:
                file_text = f.read()

            selector = Selector(text=file_text)
            img_list = selector.xpath('//img')
            for img_obj in img_list:
                img = img_obj.xpath("./@src").get('')
                if "base64," in img:
                    base64_img_path = os.path.join(self.save_dir, "base64image")
                    base64_img_name = f"{int(time.time())}.png"
                    base64_img_path_name = os.path.join(base64_img_path, base64_img_name)
                    relative_path = f"{''.join(['../' for i in range(url_layer)])}base64image/{base64_img_name}"
                    self.makedir_folder(base64_img_path)
                    file_text = file_text.replace(img, relative_path)
                    yield {"base64_img_path_name": base64_img_path_name, "base64img": img.split("base64,")[1]}
                else:
                    if "javascript" in img:
                        img = img_obj.xpath("./@data-original").get()
                    img_url, new_img_path, new_img_path_name, relative_path, dont_filter = self.get_new_sources(
                        img, url_layer)
                    if img_url:
                        file_text = file_text.replace(img, relative_path)
                        if self.is_exist(new_img_path_name):
                            self.makedir_folder(new_img_path)
                            yield scrapy.Request(img_url, callback=self.parse_image, meta=deepcopy(
                                {"new_img_path_name": new_img_path_name}
                            ), dont_filter=dont_filter, errback=self.err_callback_1)

            css_href = selector.xpath('//link[contains(@href, ".css")]/@href').getall()
            css_src = selector.xpath('//link[contains(@src, ".css")]/@src').getall()
            css_list = css_href + css_src
            for css in css_list:
                css_url, new_css_path, new_css_path_name, relative_path, dont_filter = self.get_new_sources(
                    css, url_layer)
                if css_url:
                    file_text = file_text.replace(css, relative_path)
                    if self.is_exist(new_css_path_name):
                        self.makedir_folder(new_css_path)
                        yield scrapy.Request(css_url, callback=self.parse_css, meta=deepcopy(
                            {"new_css_path_name": new_css_path_name}
                        ), dont_filter=dont_filter, errback=self.err_callback_1)

            js_list = selector.xpath('//script[contains(@src, ".js")]/@src').getall()
            for js in js_list:
                js_url, new_js_path, new_js_path_name, relative_path, dont_filter = self.get_new_sources(
                    js, url_layer)
                if js_url:
                    file_text = file_text.replace(js, relative_path)
                    if self.is_exist(new_js_path_name):
                        self.makedir_folder(new_js_path)
                        yield scrapy.Request(js_url, callback=self.parse_js, meta=deepcopy(
                            {"new_js_path_name": new_js_path_name}
                        ), dont_filter=dont_filter, errback=self.err_callback_1)

            with open(file, "w", encoding="utf-8") as f:
                f.write(file_text)

    def close(self, spider, reason):
        self.Q.put("处理完成")
        self.Q.put('爬取结束')

    def parse_image(self, response):
        item = response.meta
        item["img_body"] = response.body
        yield item

    def parse_css(self, response):
        item = response.meta
        item["css_text"] = response.text
        yield item

    def parse_js(self, response):
        item = response.meta
        item["js_text"] = response.text
        yield item
