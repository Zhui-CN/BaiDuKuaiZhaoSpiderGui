# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import base64
from twisted.internet.threads import deferToThread


class DownloadHtmlPipeline(object):
    def process_item(self, item, spider):
        if not item.get("response_test"):
            return item
        return deferToThread(self._process_item, item, spider)

    def _process_item(self, item, spider):
        response_test = item['response_test']
        url_file_path_name = item['url_file_path_name']
        try:
            with open(url_file_path_name, 'w', encoding='utf-8') as f:
                f.write(response_test)
        except:
            pass
        return item


class DownloadImagePipeline(object):
    def process_item(self, item, spider):
        if not item.get("img_body"):
            return item
        return deferToThread(self._process_item, item, spider)

    def _process_item(self, item, spider):
        img_body = item['img_body']
        new_img_path_name = item['new_img_path_name']
        try:
            with open(new_img_path_name, 'wb') as f:
                f.write(img_body)
        except:
            pass
        return item


class DownloadCssPipeline(object):
    def process_item(self, item, spider):
        if not item.get("css_text"):
            return item
        return deferToThread(self._process_item, item, spider)

    def _process_item(self, item, spider):
        css_text = item['css_text']
        new_css_path_name = item['new_css_path_name']
        try:
            with open(new_css_path_name, 'w', encoding='utf-8') as f:
                f.write(css_text)
        except:
            pass
        return item


class DownloadJsPipeline(object):
    def process_item(self, item, spider):
        if not item.get("js_text"):
            return item
        return deferToThread(self._process_item, item, spider)

    def _process_item(self, item, spider):
        js_text = item['js_text']
        new_js_path_name = item['new_js_path_name']
        try:
            with open(new_js_path_name, 'w', encoding='utf-8') as f:
                f.write(js_text)
        except:
            pass
        return item


class DownloadBase64ImagePipeline(object):
    def process_item(self, item, spider):
        if not item.get("base64img"):
            return item
        return deferToThread(self._process_item, item, spider)

    def _process_item(self, item, spider):
        base64_img_path_name = item['base64_img_path_name']
        base64img = item['base64img']
        try:
            with open(base64_img_path_name, "wb") as f:
                f.write(base64.b64decode(base64img))
        except:
            pass
        return item
