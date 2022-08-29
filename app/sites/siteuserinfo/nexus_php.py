# -*- coding: utf-8 -*-
import re

from lxml import etree

import log
from app.sites.siteuserinfo.site_user_info import ISiteUserInfo
from app.utils.string_utils import StringUtils


class NexusPhpSiteUserInfo(ISiteUserInfo):
    _site_schema = "NexusPhp"
    _brief_page = "index.php"
    _user_traffic_page = "index.php"
    _user_detail_page = "userdetails.php?id="
    _torrent_seeding_page = "getusertorrentlistajax.php?userid="

    def _parse_site_page(self, html_text):
        html_text = self._prepare_html_text(html_text)

        user_detail = re.search(r"userdetails.php\?id=(\d+)", html_text)
        if user_detail and user_detail.group().strip():
            self._user_detail_page = user_detail.group().strip().lstrip('/')
            self.userid = user_detail.group(1)
            self._torrent_seeding_page = f"getusertorrentlistajax.php?userid={self.userid}&type=seeding"
        else:
            user_detail = re.search(r"(userdetails)", html_text)
            if user_detail and user_detail.group().strip():
                self._user_detail_page = user_detail.group().strip().lstrip('/')
                self.userid = None
                self._torrent_seeding_page = None

        html = etree.HTML(html_text)
        if not html:
            self.err_msg = "未检测到已登陆，请检查cookies是否过期"
            return

        logout = html.xpath('//a[contains(@href, "logout") or contains(@data-url, "logout")'
                            ' or contains(@onclick, "logout") or contains(@href, "usercp")]')
        if not logout:
            self.err_msg = "未检测到已登陆，请检查cookies是否过期"

    def _parse_message_unread(self, html_text):
        """
        解析未读短消息数量
        :param html_text:
        :return:
        """
        html = etree.HTML(html_text)
        if not html:
            return

        message_labels = html.xpath('//a[contains(@href, "messages.php")]/..')
        if message_labels:
            message_text = message_labels[0].xpath("string(.)")

            log.debug(f"【PT】{self.site_name} 消息原始信息 {message_text}")
            message_unread_match = re.findall(r"[^Date](信息箱\s*|\(|你有\xa0)(\d+)", message_text)

            if message_unread_match and len(message_unread_match[-1]) == 2:
                self.message_unread = StringUtils.str_int(message_unread_match[-1][1])

    def _parse_user_base_info(self, html_text):
        # 合并解析，减少额外请求调用
        self.__parse_user_traffic_info(html_text)
        self._user_traffic_page = None

        self._parse_message_unread(html_text)

        html_text = self._prepare_html_text(html_text)
        user_name = re.search(r"userdetails.php\?id=\d+[a-zA-Z\"'=()\u4E00-\u9FA5_\-\s]+>[<b>\s]*([^<>]*)[</b>]*</a>",
                              html_text)
        if user_name and user_name.group(1).strip():
            self.username = user_name.group(1).strip()
            return
        html = etree.HTML(html_text)
        if not html:
            return
        ret = html.xpath('//a[contains(@href, "userdetails")]//strong//text()')
        if ret:
            self.username = str(ret[0])
            return

        ret = html.xpath('//a[contains(@href, "userdetails")]//b//text()')
        if ret:
            self.username = str(ret[0])
            return
        ret = html.xpath('//a[contains(@href, "userdetails")]//text()')
        if ret:
            self.username = str(ret[0])

    def __parse_user_traffic_info(self, html_text):
        html_text = self._prepare_html_text(html_text)
        upload_match = re.search(r"[^总]上[传傳]量?[:：_<>/a-zA-Z-=\"'\s#;]+([\d,.\s]+[KMGTPI]*B)", html_text, re.IGNORECASE)
        self.upload = StringUtils.num_filesize(upload_match.group(1).strip()) if upload_match else 0
        download_match = re.search(r"[^总子影力]下[载載]量?[:：_<>/a-zA-Z-=\"'\s#;]+([\d,.\s]+[KMGTPI]*B)", html_text,
                                   re.IGNORECASE)
        self.download = StringUtils.num_filesize(download_match.group(1).strip()) if download_match else 0
        ratio_match = re.search(r"分享率[:：_<>/a-zA-Z-=\"'\s#;]+([\d,.\s]+)", html_text)
        self.ratio = StringUtils.str_float(ratio_match.group(1)) if (
                    ratio_match and ratio_match.group(1).strip()) else 0.0
        leeching_match = re.search(r"(Torrents leeching|下载中)[\u4E00-\u9FA5\D\s]+(\d+)[\s\S]+<", html_text)
        self.leeching = StringUtils.str_int(leeching_match.group(2)) if leeching_match and leeching_match.group(
            2).strip() else 0
        html = etree.HTML(html_text)
        tmps = html.xpath('//span[@class = "ucoin-symbol ucoin-gold"]//text()') if html else None
        if tmps:
            self.bonus = StringUtils.str_float(str(tmps[-1]))
            return
        tmps = html.xpath('//a[contains(@href,"mybonus")]/text()') if html else None
        if tmps:
            bonus_text = str(tmps[0]).strip()
            bonus_match = re.search(r"([\d,.]+)", bonus_text)
            if bonus_match and bonus_match.group(1).strip():
                self.bonus = StringUtils.str_float(bonus_match.group(1))
                return
        bonus_match = re.search(r"mybonus.[\[\]:：<>/a-zA-Z_\-=\"'\s#;.(使用魔力值豆]+\s*([\d,.]+)[<()&\s]", html_text)
        try:
            if bonus_match and bonus_match.group(1).strip():
                self.bonus = StringUtils.str_float(bonus_match.group(1))
                return
            bonus_match = re.search(r"[魔力值|\]][\[\]:：<>/a-zA-Z_\-=\"'\s#;]+\s*([\d,.]+)[<()&\s]", html_text,
                                    flags=re.S)
            if bonus_match and bonus_match.group(1).strip():
                self.bonus = StringUtils.str_float(bonus_match.group(1))
        except Exception as err:
            print(str(err))

    def _parse_user_traffic_info(self, html_text):
        """
        上传/下载/分享率 [做种数/魔力值]
        :param html_text:
        :return:
        """
        pass

    def _parse_user_torrent_seeding_info(self, html_text, multi_page=False):
        """
        做种相关信息
        :param html_text:
        :param multi_page: 是否多页数据
        :return: 下页地址
        """
        html = etree.HTML(str(html_text).replace(r'\/', '/'))
        if not html:
            return None

        size_col = 3
        seeders_col = 4
        # 搜索size列
        if html.xpath('//tr[position()=1]/td[img[@class="size"] and img[@alt="size"]]'):
            size_col = len(html.xpath('//tr[position()=1]/td[img[@class="size"] '
                                      'and img[@alt="size"]]/preceding-sibling::td')) + 1
        # 搜索seeders列
        if html.xpath('//tr[position()=1]/td[img[@class="seeders"] and img[@alt="seeders"]]'):
            seeders_col = len(html.xpath('//tr[position()=1]/td[img[@class="seeders"] '
                                         'and img[@alt="seeders"]]/preceding-sibling::td')) + 1

        page_seeding = 0
        page_seeding_size = 0
        page_seeding_info = []
        seeding_sizes = html.xpath(f'//tr[position()>1]/td[{size_col}]')
        seeding_seeders = html.xpath(f'//tr[position()>1]/td[{seeders_col}]//text()')
        if seeding_sizes and seeding_seeders:
            page_seeding = len(seeding_sizes)

            for i in range(0, len(seeding_sizes)):
                size = StringUtils.num_filesize(seeding_sizes[i].xpath("string(.)").strip())
                seeders = StringUtils.str_int(seeding_seeders[i])

                page_seeding_size += size
                page_seeding_info.append([seeders, size])

        self.seeding += page_seeding
        self.seeding_size += page_seeding_size
        self.seeding_info.extend(page_seeding_info)

        # 是否存在下页数据
        next_page = None
        next_page_text = html.xpath('//a[contains(.//text(), "下一页") or contains(.//text(), "下一頁")]/@href')
        if next_page_text:
            next_page = next_page_text[-1].strip()

        return next_page

    def _parse_user_detail_info(self, html_text):
        """
        解析用户额外信息，加入时间，等级
        :param html_text:
        :return:
        """
        html = etree.HTML(html_text)
        if not html:
            return

        self.__get_user_level(html)

        # 加入日期
        join_at_text = html.xpath(
            '//tr/td[text()="加入日期" or text()="注册日期" or *[text()="加入日期"]]/following-sibling::td[1]//text()')
        if join_at_text:
            self.join_at = join_at_text[0].split(' (')[0]

        # 做种体积 & 做种数
        # seeding 页面获取不到的话，此处再获取一次
        seeding_sizes = html.xpath('//tr/td[text()="当前上传"]/following-sibling::td[1]//'
                                   'table[tr[1][td[4 and text()="尺寸"]]]//tr[position()>1]/td[4]')
        seeding_seeders = html.xpath('//tr/td[text()="当前上传"]/following-sibling::td[1]//'
                                     'table[tr[1][td[5 and text()="做种者"]]]//tr[position()>1]/td[5]//text()')
        tmp_seeding = len(seeding_sizes)
        tmp_seeding_size = 0
        tmp_seeding_info = []
        for i in range(0, len(seeding_sizes)):
            size = StringUtils.num_filesize(seeding_sizes[i].xpath("string(.)").strip())
            seeders = StringUtils.str_int(seeding_seeders[i])

            tmp_seeding_size += size
            tmp_seeding_info.append([seeders, size])

        if not self.seeding_size:
            self.seeding_size = tmp_seeding_size
        if not self.seeding:
            self.seeding = tmp_seeding
        if not self.seeding_info:
            self.seeding_info = tmp_seeding_info

        seeding_sizes = html.xpath('//tr/td[text()="做种统计"]/following-sibling::td[1]//text()')
        if seeding_sizes:
            seeding_match = re.search(r"总做种数:\s+(\d+)", seeding_sizes[0], re.IGNORECASE)
            seeding_size_match = re.search(r"总做种体积:\s+([\d,.\s]+[KMGTPI]*B)", seeding_sizes[0], re.IGNORECASE)
            tmp_seeding = StringUtils.str_int(seeding_match.group(1)) if (
                        seeding_match and seeding_match.group(1)) else 0
            tmp_seeding_size = StringUtils.num_filesize(
                seeding_size_match.group(1).strip()) if seeding_size_match else 0
        if not self.seeding_size:
            self.seeding_size = tmp_seeding_size
        if not self.seeding:
            self.seeding = tmp_seeding

        self.__fixup_torrent_seeding_page(html)

    def __fixup_torrent_seeding_page(self, html):
        """
        修正种子页面链接
        :param html:
        :return:
        """
        # 单独的种子页面
        seeding_url_text = html.xpath('//a[contains(@href,"getusertorrentlist.php") '
                                      'and contains(@href,"seeding")]/@href')
        if seeding_url_text:
            self._torrent_seeding_page = seeding_url_text[0].strip()
        # 从JS调用种获取用户ID
        seeding_url_text = html.xpath('//a[contains(@href, "javascript: getusertorrentlistajax") '
                                      'and contains(@href,"seeding")]/@href')
        csrf_text = html.xpath('//meta[@name="x-csrf"]/@content')
        if not self._torrent_seeding_page and seeding_url_text:
            user_js = re.search(r"javascript: getusertorrentlistajax\(\s*'(\d+)", seeding_url_text[0])
            if user_js and user_js.group(1).strip():
                self.userid = user_js.group(1).strip()
                self._torrent_seeding_page = f"getusertorrentlistajax.php?userid={self.userid}&type=seeding"
        elif seeding_url_text and csrf_text:
            if csrf_text[0].strip():
                self._torrent_seeding_page \
                    = f"ajax_getusertorrentlist.php"
                self._torrent_seeding_params = {'userid': self.userid, 'type': 'seeding', 'csrf': csrf_text[0].strip()}

        # 分类做种模式
        # 临时屏蔽
        # seeding_url_text = html.xpath('//tr/td[text()="当前做种"]/following-sibling::td[1]'
        #                              '/table//td/a[contains(@href,"seeding")]/@href')
        # if seeding_url_text:
        #    self._torrent_seeding_page = seeding_url_text

    def __get_user_level(self, html):
        # 等级 获取同一行等级数据，图片格式等级，取title信息，否则取文本信息
        user_levels_text = html.xpath('//tr/td[text()="等級" or text()="等级" or *[text()="等级"]]/'
                                      'following-sibling::td[1]/img[1]/@title')
        if user_levels_text:
            self.user_level = user_levels_text[0].strip()
            return

        user_levels_text = html.xpath('//tr/td[text()="等級" or text()="等级"]/'
                                      'following-sibling::td[1 and not(img)]'
                                      '|//tr/td[text()="等級" or text()="等级"]/'
                                      'following-sibling::td[1 and img[not(@title)]]')
        if user_levels_text:
            self.user_level = user_levels_text[0].xpath("string(.)").strip()
            return

        user_levels_text = html.xpath('//tr/td[text()="等級" or text()="等级"]/'
                                      'following-sibling::td[1]')
        if user_levels_text:
            self.user_level = user_levels_text[0].xpath("string(.)").strip()
            return

        user_levels_text = html.xpath('//a[contains(@href, "userdetails")]/text()')
        if not self.user_level and user_levels_text:
            for user_level_text in user_levels_text:
                user_level_match = re.search(r"\[(.*)]", user_level_text)
                if user_level_match and user_level_match.group(1).strip():
                    self.user_level = user_level_match.group(1).strip()
                    break