import sys
import os
import re
from multiprocessing import Process, Manager
from PySide2.QtCore import QThread
from PySide2.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, \
    QTextBrowser, QHBoxLayout, QVBoxLayout, QFileDialog, QCheckBox
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from BaiDuKuaiZhao.spiders.baidukuaizhao import BaiDuKuaiZhaoSpider
from BaiDuKuaiZhao.spiders.baidusite import BaiDuSiteSpider


sign_num = 0


def site_crawl(Q, url_domain, save_dir, site, inspect):
    process = CrawlerProcess(get_project_settings())
    process.crawl(BaiDuKuaiZhaoSpider, Q=Q, url_domain=url_domain, save_dir=save_dir, site=site, inspect=inspect)
    process.start()


def handle_crawl(Q, url_domain, save_dir):
    process = CrawlerProcess(get_project_settings())
    process.crawl(BaiDuSiteSpider, Q=Q, url_domain=url_domain, save_dir=save_dir)
    process.start()


class SpiderGui(QWidget):
    def __init__(self):
        super(SpiderGui, self).__init__()
        self.regex = re.compile("[\/\\\:\*\?\"\<\>\|]")
        self.p = None
        self.setWindowTitle('开始窗口')
        self.resize(500, 400)
        self.domain_line = QLineEdit(self)
        self.browse_box = QPushButton("浏览")
        self.log_browser = QTextBrowser(self)  # 日志输出框
        self.crawl_btn = QPushButton('开始爬取', self)  # 开始爬取按钮
        self.crawl_btn.clicked.connect(self.crawl_slot)
        self.browse_box.clicked.connect(self.save_addr)
        self.save_dir = QLabel("")
        self.site = QCheckBox("爬取快照")
        self.inspect = QCheckBox("检测站点")
        self.handle = QCheckBox("处理已有站点")

        self.h_layout1 = QHBoxLayout()
        self.h_layout1.addWidget(QLabel('请输入域名：'))
        self.h_layout1.addWidget(self.domain_line)

        self.h_layout2 = QHBoxLayout()
        self.h_layout2.addWidget(QLabel('保存路径：'))
        self.h_layout2.addWidget(self.save_dir)
        self.h_layout2.addWidget(self.browse_box)
        self.h_layout2.addWidget(self.site)
        self.h_layout2.addWidget(self.inspect)
        self.h_layout2.addWidget(self.handle)

        self.v_layout = QVBoxLayout()
        self.v_layout.addLayout(self.h_layout1)
        self.v_layout.addLayout(self.h_layout2)
        self.v_layout.addWidget(QLabel('日志输出框'))
        self.v_layout.addWidget(self.log_browser)
        self.v_layout.addWidget(self.crawl_btn)
        self.setLayout(self.v_layout)

        self.Q = Manager().Queue()
        self.log_thread = LogThread(self)

    def save_addr(self):
        d = QFileDialog()
        current_dir = d.getExistingDirectory()
        if current_dir == '':
            self.save_dir.setText(self.save_dir.text())
        else:
            self.save_dir.setText(current_dir)

    def crawl_slot(self):
        global sign_num
        if self.crawl_btn.text() == '开始爬取':
            self.log_browser.clear()
            url_domain = self.domain_line.text().strip()
            site = self.site.isChecked()
            inspect = self.inspect.isChecked()
            handle = self.handle.isChecked()
            if not site and not inspect and not handle:
                self.log_browser.setText('未开启其中一项功能')
            elif (handle and site) or (handle and inspect):
                self.log_browser.setText('处理已有站点只能单独使用')
            elif not os.path.exists(self.save_dir.text()):
                self.log_browser.setText('路径错误，请重新选择')
            elif not url_domain:
                self.log_browser.setText('域名为空，请重新输入')
            elif self.regex.findall(url_domain):
                self.log_browser.setText('域名不合法，请重新输入')
            else:
                sign_num = 1
                self.crawl_btn.setText('停止爬取')
                url_domain = self.domain_line.text().strip()
                save_dir = self.save_dir.text()
                if handle:
                    self.p = Process(target=handle_crawl, args=(self.Q, url_domain, save_dir))
                else:
                    self.p = Process(target=site_crawl, args=(self.Q, url_domain, save_dir, site, inspect))
                self.p.start()
                self.log_thread.start()
        else:
            self.crawl_btn.setText('开始爬取')
            self.p.terminate()
            self.log_thread.quit()
            sign_num = 0
            self.log_thread.wait()

    def closeEvent(self, event):
        if self.p and self.p.is_alive():
            self.p.terminate()
        self.log_thread.quit()
        global sign_num
        sign_num = 0
        self.log_thread.wait()


class LogThread(QThread):
    def __init__(self, gui):
        super(LogThread, self).__init__()
        self.gui = gui

    def run(self):
        while True:
            if not self.gui.Q.empty():
                self.gui.log_browser.append(self.gui.Q.get())
                cursor = self.gui.log_browser.textCursor()
                pos = len(self.gui.log_browser.toPlainText())
                cursor.setPosition(pos)
                self.gui.log_browser.setTextCursor(cursor)
                if '爬取结束' in self.gui.log_browser.toPlainText():
                    self.gui.crawl_btn.setText('开始爬取')
                    break
                self.msleep(10)
            elif not sign_num:
                break


if __name__ == '__main__':
    app = QApplication(sys.argv)
    spider_gui = SpiderGui()
    spider_gui.show()
    sys.exit(app.exec_())
