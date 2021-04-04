"""
Crawler for http://manga-panda.xyz
"""

import os
from typing import List

from bs4 import BeautifulSoup

from basemangacrawler import BaseMangaCrawler, Chapter, Page


class MangaPandaCrawler(BaseMangaCrawler):
    """
    The crawler for http://manga-panda.xyz
    """

    def __init__(self, url: str, baseDirPath: str) -> None:
        super().__init__(url, baseDirPath)

    def parseMangaTitle(self, mangaSoup: BeautifulSoup) -> str:
        """
        Parse the manga title from the soup.

        Parameters:
            mangaSoup: The HTML soup of the manga.

        Raises:
            Any and all exceptions if and when they occur.

        Returns:
            The manga title.
        """
        return mangaSoup.find('ul', 'manga-info-text').find('h1').text

    def parseChapters(self, url: str, mangaSoup: BeautifulSoup) -> List[Chapter]:
        """
        Parse the manga soup and create Chapters.

        Parameters:
            url: The URL of the manga.
            mangaSoup: The HTML soup of the manga.

        Raises:
            Any and all exceptions if and when they occur.

        Returns:
            The list of Chapters created from the soup.
        """
        result: List[Chapter] = []
        rows = mangaSoup.find('div', 'chapter-list').find_all('div', 'row')
        for i, row in enumerate(rows):
            elem = row.find('a')

            title = elem.text
            idx = len(rows) - i
            chapterUrl = elem.attrs['href']
            chapterDirname = BaseMangaCrawler.makeSafeFilename(title)
            dirPath = os.path.join(self.dirPath, chapterDirname)

            chapter = Chapter(idx, chapterUrl, dirPath, title)
            result.append(chapter)

        result = sorted(result, key=lambda item: item.idx)
        return result

    def getNextMangaPagination(self, mangaSoup: BeautifulSoup) -> str:
        """
        Get the URL of the next pagination of the manga HTML page.
        Returns None if there is no next pagination.

        Parameters:
            mangaSoup: The HTML soup of the manga.

        Raises:
            Any and all exceptions if and when they occur.

        Returns:
            The URL of the next pagination. None if there is no next pagination.
        """
        # There is no manga pagination
        return None

    def getNextChapterPagination(self, chapterSoup: BeautifulSoup) -> str:
        """
        Get the URL of the next pagination of the chapter HTML page.
        Returns None if there is no next pagination.

        Parameters:
            chapterSoup: The HTML soup of the chapter.

        Raises:
            Any and all exceptions if and when they occur.

        Returns:
            The URL of the next pagination. None if there is no next pagination.
        """
        # There is no chapter pagination
        return None

    def parseChapterTitle(self, chapter: Chapter, chapterSoup: BeautifulSoup) -> str:
        """
        Parse the chapter title from the soup.

        Parameters:
            chapter: The chapter.
            chapterSoup: The HTML soup of the chapter.

        Raises:
            Any and all exceptions if and when they occur.

        Returns:
            The chapter title.
        """
        # The chapter title has already been set, so return that instead
        return chapter.title

    def parsePages(self, url: str, chapter: Chapter, chapterSoup: BeautifulSoup) -> List[Page]:
        """
        Parse the chapter soup and create Pages.

        Parameters:
            url: The URL of the chapter.
            chapter: The chapter.
            chapterSoup: The HTML soup of the chapter.

        Raises:
            Any and all exceptions if and when they occur.

        Returns:
            The list of Pages created from the soup.
        """
        result: List[Page] = []

        # optionList = chapterSoup.find(id='page_select').find_all('option')
        # for idx, option in enumerate(optionList):
        #     imageUrl = option.attrs['value']
        #     dirPath = chapter.dirPath
        #     page = Page(idx + 1, url, dirPath, imageUrl)
        #     result.append(page)

        arrayDataStr = chapterSoup.find(id='arraydata').text

        urls = [url.strip() for url in arrayDataStr.split(',')]
        for idx, imageUrl in enumerate(urls):
            page = Page(idx + 1, url, chapter.dirPath, imageUrl)
            result.append(page)

        return result

    def parseImageUrl(self, pageSoup: BeautifulSoup) -> str:
        """
        Parse the image URL from the soup.

        Parameters:
            pageSoup: The HTML soup of the chapter.

        Raises:
            Any and all exceptions if and when they occur.

        Returns:
            The image URL.
        """
        # This function should never be called, because the imageUrl
        # should already have been provided when the Page was instantiated.
        raise NotImplementedError
