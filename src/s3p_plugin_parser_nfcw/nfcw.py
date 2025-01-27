import datetime
import time

from s3p_sdk.exceptions.parser import S3PPluginParserFinish, S3PPluginParserOutOfRestrictionException
from s3p_sdk.plugin.payloads.parsers import S3PParserBase
from s3p_sdk.types import S3PRefer, S3PDocument, S3PPlugin, S3PPluginRestrictions
from s3p_sdk.types.plugin_restrictions import FROM_DATE
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
import dateutil.parser

class NFCW(S3PParserBase):
    """
    A Parser payload that uses S3P Parser base class.
    """
    HOST = "https://www.nfcw.com"
    def __init__(self, refer: S3PRefer, plugin: S3PPlugin, restrictions: S3PPluginRestrictions, web_driver: WebDriver):
        super().__init__(refer, plugin, restrictions)

        # Тут должны быть инициализированы свойства, характерные для этого парсера. Например: WebDriver
        self._driver = web_driver
        self._wait = WebDriverWait(self._driver, timeout=20)


    def _parse(self):
        """
                Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
                :return:
                :rtype:
                """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -

        for page in self._encounter_years_of_pages():
            # Получение URL новой страницы
            links = []
            for link in self._collect_doc_links(page):
                # Запуск страницы и ее парсинг
                self._parse_news_page(link)

    def _encounter_years_of_pages(self) -> str:
        _base = self.HOST
        _params = '/'
        year = int(datetime.datetime.now().year)
        while True:
            url = _base + '/' + str(year) + '/'
            year -= 1
            yield url

    def _collect_doc_links(self, url: str) -> list[str]:
        """
        Сбор ссылок из архива одного года
        :param url:
        :return:
        """
        try:
            self._initial_access_source(url)
        except Exception as e:
            raise NoSuchElementException() from e

        self._wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, '.site-main')))

        links = []

        while True:
            self.logger.debug('Загрузка списка элементов...')
            doc_table = self._driver.find_element(By.CLASS_NAME, 'site-main').find_elements(By.XPATH,
                                                                                            '//article[contains(@class,\'\')]')
            self.logger.debug('Обработка списка элементов...')

            for i, element in enumerate(doc_table):
                try:
                    link = element.find_element(By.XPATH, './/*[contains(@class,\'entry-content\')]').find_element(
                        By.TAG_NAME, 'a').get_attribute('href')
                    links.append(link)
                except Exception as e:
                    self.logger.debug(f'Doc link not found: {e}')

            try:
                # // *[ @ id = "all-materials"] / font[2] / a[5]
                pagination_arrow = self._driver.find_element(By.CLASS_NAME, 'nextpostslink')
                # pg_num = pagination_arrow.get_attribute('href')
                self._driver.execute_script('arguments[0].click()', pagination_arrow)
                time.sleep(3)
                self.logger.debug(f'Выполнен переход на след. страницу: ')
            except:
                self.logger.warning('Не удалось найти переход на след. страницу. Прерывание цикла обработки')
                break

        return links

    def _parse_news_page(self, url: str) -> None:

        self.logger.debug(f'Start parse document by url: {url}')

        try:
            self._initial_access_source(url, 3)

            _title = self._driver.find_element(By.CLASS_NAME, 'entry-title').text  # Title: Обязательное поле
            el_date = self._driver.find_element(By.CLASS_NAME, 'published')
            _published = dateutil.parser.parse(el_date.get_attribute('datetime'))
            _published = _published.replace(tzinfo=None)
            _weblink = url
        except Exception as e:
            raise NoSuchElementException(
                'Страница не открывается или ошибка получения обязательных полей') from e
        else:
            document = S3PDocument(
                None,
                _title,
                None,
                None,
                _weblink,
                None,
                {},
                _published,
                datetime.datetime.now()
            )
            try:
                _meta = self._driver.find_element(By.XPATH, '//article/header/div[@class="entry-meta"]')
                _author = _meta.find_element(By.CLASS_NAME, 'author').text
                if _author:
                    document.other_data['author'] = _author
            except:
                self.logger.debug('There isn\'t author in the page')

            try:
                _text = self._driver.find_element(By.XPATH, '//article/div[@class="entry-content"]').text
                if _text:
                    document.text = _text
            except:
                self.logger.debug('There isn\'t a main text in the page')

            try:
                tags = self._driver.find_element(By.CLASS_NAME, 'tags-links')
                els = tags.find_elements(By.TAG_NAME, 'a')
                if els:
                    document.other_data['explore_tags'] = []
                for el in els:
                    tg_title = el.get_attribute('title')
                    tg_href = el.get_attribute('href')
                    document.other_data.get('explore_tags').append({'title': tg_title, 'href': tg_href})
            except:
                self.logger.debug('There aren\'t an explore tags in the page')

            try:
                tags = self._driver.find_element(By.CLASS_NAME, 'technologies-links')
                els = tags.find_elements(By.TAG_NAME, 'a')
                if els:
                    document.other_data['technologies_tags'] = []
                for el in els:
                    tg_title = el.get_attribute('title')
                    tg_href = el.get_attribute('href')
                    document.other_data.get('technologies_tags').append({'title': tg_title, 'href': tg_href})
            except:
                self.logger.debug('There aren\'t technologies tags in the page')

            try:
                tags = self._driver.find_element(By.CLASS_NAME, 'countries-links')
                els = tags.find_elements(By.TAG_NAME, 'a')
                if els:
                    document.other_data['countries_tags'] = []
                for el in els:
                    tg_title = el.get_attribute('title')
                    tg_href = el.get_attribute('href')
                    document.other_data.get('countries_tags').append({'title': tg_title, 'href': tg_href})
            except:
                self.logger.debug('There aren\'t countries tags in the page')

            try:
                self._find(document)
            except S3PPluginParserOutOfRestrictionException as e:
                if e.restriction == FROM_DATE:
                    self.logger.debug(f'Document is out of date range `{self._restriction.from_date}`')
                    raise S3PPluginParserFinish(self._plugin,
                                                f'Document is out of date range `{self._restriction.from_date}`', e)

    def _initial_access_source(self, url: str, delay: int = 2):
        self._driver.get(url)
        self.logger.debug('Entered on web page ' + url)
        time.sleep(delay)
        self._agree_cookie_pass()

    def _agree_cookie_pass(self):
        """
        Метод прожимает кнопку agree на модальном окне
        """
        cookie_agree_xpath = '//*[@id="onetrust-accept-btn-handler"]'

        try:
            cookie_button = self._driver.find_element(By.XPATH, cookie_agree_xpath)
            if WebDriverWait(self._driver, 5).until(ec.element_to_be_clickable(cookie_button)):
                cookie_button.click()
                self.logger.debug(F"Parser pass cookie modal on page: {self._driver.current_url}")
        except NoSuchElementException as e:
            self.logger.debug(f'modal agree not found on page: {self._driver.current_url}')

