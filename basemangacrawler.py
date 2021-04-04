"""
An abstract base class for a Manga with Chapters.
"""

import os
import shutil
import logging
from time import sleep
from typing import List
from queue import Empty, Queue
from functools import lru_cache
from threading import Thread, Event
from abc import ABC, abstractmethod

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)
console = logging.getLogger("console")


####################################################################################################
#  PAGE
####################################################################################################

class Page:
    """
    The page of the manga.

    Parameters:
        idx: The index/order of the page.
        pageUrl: The main URL of the HTML of the page.
        dirPath: The path of the directory where the page image will be saved.
        imageUrl: The URL of the page image.
    """

    def __init__(self, idx: int, pageUrl: str, dirPath: str, imageUrl: str = None) -> None:
        if idx < 1:
            raise ValueError('The index must be a positive number.')

        if pageUrl is None or pageUrl == '':
            raise ValueError('The pageUrl must not be None.')

        if dirPath is None or dirPath == '':
            raise ValueError('The dirPath must not be None.')

        self.idx: int = idx
        self.pageUrl: str = pageUrl
        self.dirPath: str = dirPath
        self.imageUrl: str = imageUrl

    def fileExists(self) -> bool:
        """
        Returns true if the downloaded image already exists.
        Returns false if the filepath is None or if the downloaded image does not exist.
        """
        filepath = self.filepath
        if filepath is None:
            return False
        return os.path.exists(filepath)

    @property
    def filename(self) -> str:
        """
        The filename of the downloaded image.
        None if the imageUrl is None.
        """
        if self.imageUrl is None:
            return None
        _, ext = os.path.splitext(self.imageUrl)
        return f'page{self.idx:04}{ext}'

    @property
    def filepath(self) -> str:
        """
        The filepath of the downloaded image.
        None if the filename is None.
        """
        filename = self.filename
        if filename is None:
            return None
        return os.path.join(self.dirPath, filename)

    def download(self) -> None:
        """
        Download the image.

        Raises:
            An exception if anything went wrong while downloading image.
        """
        if self.imageUrl is None:
            logger.error('Cannot download page %d (%s), imageUrl is None.', self.idx, self.pageUrl)
            raise ValueError('Cannot download image, imageUrl is None.')

        response = requests.get(self.imageUrl, stream=True)
        response.raise_for_status()

        if not os.path.exists(self.dirPath):
            os.makedirs(self.dirPath)

        with open(self.filepath, 'wb') as outputFile:
            shutil.copyfileobj(response.raw, outputFile)

        del response

    def toDict(self) -> dict:
        """
        Returns the dictionary representation of the Page.
        """
        return {
            'idx': self.idx,
            'pageUrl': self.pageUrl,
            'dirPath': os.path.abspath(self.dirPath),
            'imageUrl': self.imageUrl
        }


####################################################################################################
#  CHAPTER
####################################################################################################

class Chapter:
    """
    The chapter of the manga.

    Parameters:
        idx: The index/order of the chapter. Note that this may be different from
             the chapter title if there are some special chapters (e.g. Chapter 10.5).
        url: The main URL of the chapter.
        dirPath: The path of the directory where the chapter will be saved.
        title: The title of the chapter. If None, the title will be set to the index.
        pages: The pages of the chapter.
    """

    def __init__(self, idx: int, url: str, dirPath: str, title: str = None,
                 pages: List[Page] = None) -> None:

        if idx < 1:
            logger.error('Failed to initialize chapter, index %d is invalid.', idx)
            raise ValueError('The index must be a positive number.')

        if url is None or url == '':
            logger.error('Failed to initialize chapter %d, URL is None.', idx)
            raise ValueError('The URL must not be None.')

        if title is None:
            title = f'chapter{idx:04}'

        self.idx: int = idx
        self.url: str = url
        self.title: str = title
        self.dirPath: str = dirPath
        self.pages: List[Page] = [] if pages is None else pages

    @property
    def hasPages(self) -> bool:
        """
        True if the pages list is populated with pages. False otherwise.
        """
        return self.pages is not None and len(self.pages) > 0

    @property
    def isDownloaded(self) -> bool:
        """
        True if the pages list is populated with pages and all of them
        have already been downloaded. False otherwise.
        """
        return self.hasPages and all(page.fileExists() for page in self.pages)

    def toDict(self) -> dict:
        """
        Returns the dictionary representation of the Chapter.
        """
        return {
            'idx': self.idx,
            'url': self.url,
            'title': self.title,
            'dirPath': os.path.abspath(self.dirPath),
            'pages': [page.toDict() for page in self.pages]
        }


####################################################################################################
#  BASE MANGA CRAWLER
####################################################################################################

class BaseMangaCrawler(ABC):
    """
    An abstract base class for a Manga.

    Attributes:
        url: The main URL of the manga.
        baseDirPath: The path of the base output directory.
        dirPath: The path of the directory where the manga will be saved.
        cachePath: The path of the JSON cache file.
        title: The title of the manga.
        chapters: The chapters of the manga.
        numChapterThreads: The number of chapter processing threads.
        numPageThreads: The number of page downloading threads.

    Raises:
        ValueError: When the given parameters are invalid.
        FileNotFoundError: When the cachePath is specified, but file was not found.
    """

    def __init__(self, url: str, baseDirPath: str, dirPath: str = None,
                 cachePath: str = None, title: str = None, chapters: List[Chapter] = None,
                 numChapterThreads: int = 3, numPageThreads: int = 5) -> None:

        super().__init__()

        if url is None or url == '':
            logger.error('Failed to initialize Manga, URL is None.')
            raise ValueError('The URL must not be None.')

        if baseDirPath is None or baseDirPath == '':
            logger.error('Failed to initialize Manga, baseDirPath is None.')
            raise ValueError('The baseDirPath must not be None.')

        if cachePath is not None and not os.path.exists(cachePath):
            logger.error('Failed to initialize Manga, cache file not found at %s.', cachePath)
            raise FileNotFoundError(f'Cache file not found at {cachePath}.')

        if numChapterThreads < 1:
            logger.error('Failed to initialize Manga, invalid numChapterThreads: %d.',
                         numChapterThreads)
            raise ValueError('Invalid number of chapter processing threads.')

        if numPageThreads < 1:
            logger.error('Failed to initialize Manga, invalid numPageThreads: %d.',
                         numPageThreads)
            raise ValueError('Invalid number of page downloading threads.')

        self.url: str = url
        self.title: str = title
        self.baseDirPath: str = baseDirPath
        self.dirPath: str = dirPath
        self.cachePath: str = cachePath
        self.chapters: List[Chapter] = [] if chapters is None else chapters

        self.numChapterThreads: int = numChapterThreads     # The number of chapter threads
        self.numPageThreads: int = numPageThreads           # The number of page threads

        self._killEvent = Event()       # Terminates the download

        self._chapterQueue = Queue()    # The chapter processing queue
        self._pageQueue = Queue()       # The page processing queue

        self._chapterThreads: List[Thread] = []     # The chapter worker threads
        self._pageThreads: List[Thread] = []        # The page worker threads

        self._chapterProgress: tqdm = None  # The chapter progress bar
        self._pageProgress: tqdm = None     # The page progress bar

    def toDict(self) -> dict:
        """
        Returns the dictionary representation of the MangaCrawler.
        """
        return {
            'url': self.url,
            'title': self.title,
            'baseDirPath': os.path.abspath(self.baseDirPath),
            'dirPath': os.path.abspath(self.dirPath),
            'cachePath': os.path.abspath(self.cachePath),
            'numChapterThreads': self.numChapterThreads,
            'numPageThreads': self.numPageThreads,
            'chapters': [chapter.toDict() for chapter in self.chapters]
        }
    def terminate(self) -> None:
        """
        Terminate the download by setting the kill event.
        """
        logger.info('----- [%s] Kill event is set -----', self.url)
        self._killEvent.set()

        if self._chapterProgress is not None:
            self._chapterProgress.close()

        if self._pageProgress is not None:
            self._pageProgress.close()

    def download(self) -> None:
        """
        Download the manga
        """
        if self.url is None:
            logger.error('Cannot download manga, the URL is None.')
            console.error('Cannot download manga, the URL is None.')
            return

        logger.info('----- Starting download for %s -----', self.url)

        # Initialize the title if it hasn't been set yet
        self._initMangaTitle()

        # If the title still hasn't been set, terminate download
        if self.title is None or self.title == '':
            console.error('Terminating download, failed to get manga title.')
            return

        console.info('Manga title: %s', self.title)

        # Set the manga's dirPath
        if self.dirPath is None or self.dirPath == '':
            dirName = BaseMangaCrawler.makeSafeFilename(self.title)
            self.dirPath = os.path.join(self.baseDirPath, dirName)

        # Fetch the chapters from the paginated manga HTML
        chapterList = self._fetchChapters()
        if chapterList is None:
            return

        if self._killEvent.is_set():
            return

        # Populate the chapter queue
        self._chapterQueue = Queue()
        for chapter in chapterList:
            self._chapterQueue.put(chapter)

        self._chapterProgress = tqdm(total=len(chapterList),
                                     desc='Chapter Processing', unit='chapters')
        self._pageProgress = tqdm(total=0, desc='Page Download', unit='pages')

        # Start the chapter threads
        self._chapterThreads = []
        for _ in range(self.numChapterThreads):
            t = Thread(target=self.processChapter)
            self._chapterThreads.append(t)
            t.start()

        # Start the page threads
        self._pageThreads = []
        for _ in range(self.numPageThreads):
            t = Thread(target=self.processPage)
            self._pageThreads.append(t)
            t.start()

        # Wait for the threads to finish
        while any(t.is_alive() for t in self._chapterThreads):
            sleep(0.3)
        while any(t.is_alive() for t in self._pageThreads):
            sleep(0.3)

        for t in self._chapterThreads:
            t.join()
        for t in self._pageThreads:
            t.join()

        # Close the progress bars
        self._chapterProgress.close()
        self._pageProgress.close()

    #################################################################
    #  WORKER THREAD METHODS
    #################################################################

    def processChapter(self) -> None:
        """
        Work function of the chapter threads.
        """
        while True:
            if self._killEvent.is_set():
                return

            if not self._chapterQueue.empty():
                try:
                    # Get the chapter without blocking
                    chapter: Chapter = self._chapterQueue.get(block=False)

                    # Set the chapter title
                    chapter.title = self._fetchChapterTitle(chapter)

                    # Fetch the chapter's pages
                    pages = self._fetchPages(chapter)
                    if pages is None:
                        # Terminate thread if return value is None
                        return

                    # Append the pages into the page queue
                    for page in pages:
                        self._pageQueue.put((page, chapter))

                    # Update the progress bar total
                    self._pageProgress.total = self._pageProgress.total + len(pages)
                    self._chapterProgress.update()

                    self._chapterQueue.task_done()

                except Empty:
                    # Just continue the loop if the queue is empty
                    continue

                except Exception as err:  # pylint: disable=broad-except
                    chapterTitle = chapter.title if chapter is not None else 'Unknown Chapter'
                    logger.exception('[%s] Something went wrong while processing %s, %s',
                                     self.title, chapterTitle, err)
                    self._chapterProgress.write(f'Failed to process {chapterTitle}.')
                    self._chapterProgress.update()
                    self._chapterQueue.task_done()
                    continue

            else:  # If chapter queue is empty
                self._chapterProgress.refresh()
                break

    def processPage(self) -> None:
        """
        Work function of the page threads.
        """
        while True:
            if self._killEvent.is_set():
                return

            page: Page = None
            chapter: Chapter = None
            if not self._pageQueue.empty():
                try:
                    page, chapter = self._pageQueue.get(block=False)

                    # Cannot process if both pageUrl and imageUrl are not set
                    if page.pageUrl is None and page.imageUrl is None:
                        chapterTitle = chapter.title if chapter.title is not None \
                            else f'Chapter{chapter.idx:04}'
                        logger.exception("[%s] Failed to process page %d of %s, "
                                         "pageUrl and imageUrl are both None.",
                                         self.title, page.idx, chapterTitle)
                        self._chapterProgress.write(f'Cannot process page {page.idx} '
                                                    f'of {chapterTitle}, cannot find URL.')
                        self._pageProgress.update()
                        self._pageQueue.task_done()
                        continue

                    # Fetch the page HTML and parse the image URL from there
                    if page.imageUrl is None:
                        soup = BaseMangaCrawler.fetchHtmlSoup(page.pageUrl)
                        # self.parseImageUrl should not return None.
                        # Instead, it should raise an exception if something went wrong.
                        page.imageUrl = self.parseImageUrl(soup)

                    # Check the kill event before downloading the image
                    if self._killEvent.is_set():
                        return

                    # Download the image
                    page.download()

                    self._pageProgress.update()
                    self._pageQueue.task_done()

                except Empty:
                    # Just continue the loop if the queue is empty
                    continue

                except Exception as err:  # pylint: disable=broad-except
                    pageNum = f'Page{page.idx:04}'
                    chapterTitle = chapter.title if chapter.title is not None \
                        else f'Chapter{chapter.idx:04}'
                    logger.exception('[%s] Something went wrong while processing %s of %s, %s',
                                     self.title, pageNum, chapterTitle, err)
                    self._pageProgress.update()
                    self._pageQueue.task_done()
                    continue

            else:  # If page queue is empty
                if self._killEvent.is_set():
                    return

                # If all chapter threads are all dead/finished
                if all(not t.is_alive() for t in self._chapterThreads):
                    return

                sleep(0.1)

    #################################################################
    #  PRIVATE METHODS
    #################################################################

    def _initMangaTitle(self) -> None:
        """
        If the manga title hasn't been set yet,
        fetch the manga soup and initialize the title.
        """
        if self.url is None or self.url == '':
            logger.error('Failed to initialize manga title, manga URL is None.')
            raise ValueError('Manga URL must not be None.')

        if self.title is not None and self.title != '':
            # Do nothing if title is already set
            return

        try:
            soup = BaseMangaCrawler.fetchHtmlSoup(self.url)
        except Exception as err:  # pylint: disable=broad-except
            logger.exception('Failed to fetch manga HTML: %s, %s', self.url, err)
            return

        try:
            self.title = self.parseMangaTitle(soup)
        except Exception as err:  # pylint: disable=broad-except
            logger.exception('Failed to parse manga title from %s, %s', self.url, err)

    def _fetchChapters(self) -> List[Chapter]:
        """
        Fetch all paginations of the manga and parse all chapters.

        Returns:
            The list of Chapters. Returns None if something went wrong
            or if the kill event was set.
        """
        result: List[Chapter] = []

        url = self.url
        while url is not None:
            # If kill event is set, stop the download
            if self._killEvent.is_set():
                return None

            console.info('Fetching chapters from %s...', url)

            try:
                # Fetch the manga HTML of the current pagination
                soup = BaseMangaCrawler.fetchHtmlSoup(url)

                # Get all the chapters from this paginated manga soup and append it to the list
                chapters = self.parseChapters(url, soup)
                result.extend(chapters)

                # Get the URL of the next manga HTML pagination
                url = self.getNextMangaPagination(soup)

            except Exception as err:  # pylint: disable=broad-except
                logger.exception('[%s] Failed to load chapters from %s, %s', self.title, url, err)
                console.error('Failed to load the manga URL: %s', url)
                return None

        # If no exception was raised while fetching or parsing
        # but the chapter queue is empty, there is nothing to process
        if len(result) == 0:
            console.info("No chapters were found for '%s'.", self.title)
            return None

        if self._killEvent.is_set():
            return None

        return result

    def _fetchChapterTitle(self, chapter) -> str:
        """
        Fetch the main chapter HTML and parse the title.
        Returns the currently set chapter title if something went wrong.

        Returns:
            The title of the chapter.
        """
        try:
            title = chapter.title
            soup = BaseMangaCrawler.fetchHtmlSoup(chapter.url)
            title = self.parseChapterTitle(chapter, soup)
        except Exception as err:  # pylint: disable=broad-except
            logger.exception('[%s] Failed to fetch chapter title from %s, %s',
                             self.title, chapter.url, err)
        return title

    def _fetchPages(self, chapter) -> List[Page]:
        """
        Fetch all paginations of the chapter and parse all pages.
        If the return value is None, the thread will terminate.

        Returns:
            The list of Pages. Returns None if something went wrong
            or if the kill event was set.
        """
        result: List[Page] = []
        chapter.pages = []

        url = chapter.url
        while url is not None:
            # Terminate the thread if kill event is set
            if self._killEvent.is_set():
                return None

            try:
                # Fetch the chapter HTML of the current pagination
                soup = BaseMangaCrawler.fetchHtmlSoup(url)

                # Get all the pages from this paginated chapter soup and append it to the list
                pages = self.parsePages(url, chapter, soup)
                result.extend(pages)
                chapter.pages.extend(pages)

                # Get the URL of the next chapter HTML pagination
                url = self.getNextChapterPagination(soup)

            except Exception as err:  # pylint: disable=broad-except
                logger.exception('[%s] Failed to load pages of %s from %s, %s',
                                 self.title, chapter.title, url, err)
                self._chapterProgress.write(f'Failed to load the chapter URL: {url}')
                break

        return result

    #################################################################
    #  ABSTRACT METHODS
    #################################################################

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def isMangaPaginated(self) -> bool:
        """
        Returns true if the manga is paginated.
        In other words, if not all chapters are listed on the main manga HTML page.
        """

    @abstractmethod
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

    @abstractmethod
    def isChapterPaginated(self) -> bool:
        """
        Returns true if the chapter is paginated.
        In other words, if not all pages are listed on the chapter HTML page.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    #################################################################
    #  HELPER METHODS
    #################################################################

    @staticmethod
    @lru_cache(maxsize=32)
    def fetchHtmlSoup(url: str) -> BeautifulSoup:
        """
        Fetch an HTML page and return its soup.
        Raises an error if the fetching or the parsing failed.
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        except Exception as err:
            logger.exception('Failed to fetch HTML soup of %s, %s', url, err)
            raise err

    @staticmethod
    @lru_cache(maxsize=32)
    def makeSafeFilename(filename: str) -> str:
        """
        Makes the filename Windows-safe by removing unsafe characters.
        """
        keepChars = (' ', '.', '_', '-', "'", '(', ')')
        return "".join(c for c in filename if c.isalnum() or c in keepChars).strip()
