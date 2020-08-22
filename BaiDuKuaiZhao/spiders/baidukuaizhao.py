# -*- coding: utf-8 -*-

import scrapy
import time
import re
import os
from multiprocessing import Manager
from urllib.parse import urlparse, urljoin
from copy import deepcopy


class BaiDuKuaiZhaoSpider(scrapy.Spider):
    name = 'baidukuaizhao'
    regex = re.compile("[\/\\\:\*\?\"\<\>\|]", re.S)
    regex_404 = re.compile(r'404.*?错误', re.S)

    def __init__(self, url_domain, save_dir, Q=None, site=False, inspect=True):
        super(BaiDuKuaiZhaoSpider, self).__init__()
        self.url_domain = url_domain
        self.work_path = os.path.join(save_dir, url_domain)
        self.site = site
        self.inspect = inspect
        self.die_list = []
        self.start_urls = [f'https://www.baidu.com/s?wd=site%3A{url_domain}&pn=0&oq=site%3A{url_domain}&rn=10&ie=utf-8']
        self.Q = Q if Q else Manager().Queue()
        self.Q.put('开始爬取')

    def is_survival(self, response):
        if self.regex_404.search(response.text):
            item = response.meta
            self.die_list.append(
                {"title": item['title'], 'url': response.url}
            )
        if not self.site:
            title = response.meta['title']
            self.Q.put(title)

    def err_callback_1(self, error):
        req = error.request
        item = req.meta
        self.die_list.append(
            {"title": item['title'], 'url': req.url}
        )
        
    def err_callback_2(self, error):
        pass

    def makedir_folder(self, source_path):
        if not os.path.exists(source_path):
            os.makedirs(source_path)

    def is_exist(self, file_path_name):
        if not os.path.exists(file_path_name):
            return True
        return False

    def get_new_sources(self, sources, url_head, current_path, url_layer):
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
            resources_url = urljoin(url_head, sources.replace('/', '', 1))
        elif sources.endswith(".png") or sources.endswith(".jpg") or sources.endswith(".jpeg") or sources.endswith(
                ".css") or sources.endswith(".js"):
            resources_url = urljoin(url_head, sources)
        else:
            return None, None, None, None, None

        sources_urlparse_path = urlparse(resources_url).path
        sources_path = os.path.dirname(sources_urlparse_path).replace('/', '', 1)
        sources_name = os.path.basename(sources_urlparse_path)
        if not sources_name:
            sources_name = str(int(time.time()))
        sources_name = self.regex.sub("", sources_name)

        new_sources_path = os.path.join(current_path, sources_path)
        new_sources_path_name = os.path.join(new_sources_path, sources_name)
        relative_path = os.path.join(sources_path, sources_name)
        relative_path = f"{''.join(['../' for i in range(url_layer)])}{relative_path}"

        return resources_url, new_sources_path, new_sources_path_name, relative_path, dont_filter

    def parse(self, response, **kwargs):
        lis_list = response.xpath('//div[@tpl="se_com_default"]')
        if self.inspect:
            for lis_li in lis_list:
                url = lis_li.xpath('./h3/a/@href').get()
                title = ''.join(lis_li.xpath('./h3/a//text()').getall()).strip()
                yield scrapy.Request(url, callback=self.is_survival, meta=deepcopy({
                    'title': title}), errback=self.err_callback_1)

        if self.site:
            for snapshot_li in lis_list:
                snapshot_url = snapshot_li.xpath('.//*[text()="百度快照"]/@href').get()
                yield scrapy.Request(snapshot_url, callback=self.parse_item, errback=self.err_callback_2)

        next_url = response.xpath('//*[contains(text(),"下一页")]/@href').get()
        if next_url:
            next_url = response.urljoin(next_url)
            yield scrapy.Request(next_url, callback=self.parse, errback=self.err_callback_2)

    def parse_item(self, response):
        title = response.xpath("//title/text()").get(str(int(time.time()))).replace('\n', '').strip()
        title = self.regex.sub("", title)

        base_url = response.xpath("//base/@href").get()
        if not base_url:
            base_url = response.url
            response_test = response.text
        else:
            temp = response.xpath("//div[@style='position:relative']").get()
            temp = temp.split('<div style="position:relative">')[1].rsplit("</div>", 1)[0]
            response_test = temp

        response_test = response_test.replace("gb2312", "utf-8").replace("gbk", "utf-8")

        source_url = urlparse(base_url)

        target_domain = source_url.netloc.replace(":", "_")

        current_path = os.path.join(self.work_path, target_domain)

        target_path = source_url.path
        url_path = os.path.dirname(target_path)
        url_file_name = os.path.basename(target_path)

        if not url_file_name:
            url_file_name = "index.html"
        elif "." not in url_file_name:
            url_file_name = f'{url_file_name}.html'

        if url_path == '/' or url_path == '':
            url_layer = 0
            url_file_path_name = os.path.join(current_path, url_file_name)
        else:
            url_layer = url_path.count("/")
            url_file_path_name = os.path.join(current_path, url_path.replace('/', '', 1), url_file_name)

        url_head = f'{source_url.scheme}://{target_domain}'

        img_list = response.xpath('//img')
        for img_obj in img_list:
            img = img_obj.xpath("./@src").get('')
            if "base64," in img:
                base64_img_path = os.path.join(current_path, "base64image")
                base64_img_name = f"{int(time.time())}.png"
                base64_img_path_name = os.path.join(base64_img_path, base64_img_name)
                relative_path = f"{''.join(['../' for i in range(url_layer)])}base64image/{base64_img_name}"
                self.makedir_folder(base64_img_path)
                response_test = response_test.replace(img, relative_path)
                yield {"base64_img_path_name": base64_img_path_name, "base64img": img.split("base64,")[1]}
            else:
                if "javascript" in img:
                    img = img_obj.xpath("./@data-original").get()

                img_url, new_img_path, new_img_path_name, relative_path, dont_filter = self.get_new_sources(
                    img, url_head, current_path, url_layer
                )
                if img_url:
                    response_test = response_test.replace(img, relative_path)
                    if self.is_exist(new_img_path_name):
                        self.makedir_folder(new_img_path)
                        yield scrapy.Request(img_url, callback=self.parse_image, meta=deepcopy(
                            {"new_img_path_name": new_img_path_name}
                        ), dont_filter=dont_filter, errback=self.err_callback_2)

        css_href = response.xpath('//link[contains(@href, ".css")]/@href').getall()
        css_src = response.xpath('//link[contains(@src, ".css")]/@src').getall()
        css_list = css_href + css_src
        for css in css_list:
            css_url, new_css_path, new_css_path_name, relative_path, dont_filter = self.get_new_sources(
                css, url_head, current_path, url_layer
            )
            if css_url:
                response_test = response_test.replace(css, relative_path)
                if self.is_exist(new_css_path_name):
                    self.makedir_folder(new_css_path)
                    yield scrapy.Request(css_url, callback=self.parse_css, meta=deepcopy(
                        {"new_css_path_name": new_css_path_name}
                    ), dont_filter=dont_filter, errback=self.err_callback_2)

        js_list = response.xpath('//script[contains(@src, ".js")]/@src').getall()
        for js in js_list:
            js_url, new_js_path, new_js_path_name, relative_path, dont_filter = self.get_new_sources(
                js, url_head, current_path, url_layer
            )
            if js_url:
                response_test = response_test.replace(js, relative_path)
                if self.is_exist(new_js_path_name):
                    self.makedir_folder(new_js_path)
                    yield scrapy.Request(js_url, callback=self.parse_js, meta=deepcopy(
                        {"new_js_path_name": new_js_path_name}
                    ), dont_filter=dont_filter, errback=self.err_callback_2)

        self.Q.put(title)
        self.makedir_folder(os.path.dirname(url_file_path_name))
        yield {"response_test": response_test, "url_file_path_name": url_file_path_name}

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

    def close(self, spider, reason):
        if self.inspect:
            self.Q.put("无效链接为：")
            for die in self.die_list:
                self.Q.put(str(die))
        self.Q.put('爬取结束')

# if __name__ == '__main__':
#     from scrapy.cmdline import execute
#     a = r"scrapy crawl baidukuaizhao -a url_domain=hunbovps.com -a work_path=C:\Users\Zhui\Desktop\hunbovps.com".split()
#     execute(a)
