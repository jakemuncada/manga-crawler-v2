"""
Module to crawl manga sites and download manga.
"""

import os
import logging
from typing import List
from logging.handlers import RotatingFileHandler

import argh
from argh.decorators import arg

from basemangacrawler import BaseMangaCrawler
from manganelocrawler import ManganeloCrawler
from mangapandacrawler import MangaPandaCrawler


logger = logging.getLogger(__name__)
console = logging.getLogger("console")


@arg('url', help='The main URL of the manga to be downloaded.')
@arg('-o', '--output', help='The output path of the manga.')
@arg('-c', '--cthreads', type=int, help='The number of chapter processing threads.')
@arg('-p', '--pthreads', type=int, help='The number of page downloading threads.')
def manganelo(url: str, output: str = "./output", cthreads: int = 3, pthreads: int = 5):
    """
    Download a manga from https://manganelo.com.
    """
    crawler = ManganeloCrawler(url, output)
    crawler.numChapterThreads = cthreads
    crawler.numPageThreads = pthreads
    crawler.download()


@arg('url', help='The main URL of the manga to be downloaded.')
@arg('-o', '--output', help='The output path of the manga.')
@arg('-c', '--cthreads', type=int, help='The number of chapter processing threads.')
@arg('-p', '--pthreads', type=int, help='The number of page downloading threads.')
def mangapanda(url: str, output: str = "./output", cthreads: int = 3, pthreads: int = 5):
    """
    Download a manga from https://manga-panda.xyz.
    """
    crawler = MangaPandaCrawler(url, output)
    crawler.numChapterThreads = cthreads
    crawler.numPageThreads = pthreads
    crawler.download()


@arg('-f', '--filepath', help='The input filepath.  \
    Each manga to be downloaded is listed in the input file.')
@arg('-o', '--output', help='The output path of the manga.')
@arg('-c', '--cthreads', type=int, help='The number of chapter processing threads.')
@arg('-p', '--pthreads', type=int, help='The number of page downloading threads.')
def download(filepath: str = './urls.txt', output: str = './output',
             cthreads: int = 3, pthreads: int = 5):
    """
    Download a list of manga. An input file is required.
    The input file should be either a JSON file or a txt file.
    """
    if cthreads < 1:
        console.error('Invalid number of chapter processing threads.')
        return

    if pthreads < 1:
        console.error('Invalid number of page downloading threads.')
        return

    if not os.path.exists(filepath):
        console.error('The input file at %s does not exist', filepath)
        return

    urls: List[str] = []
    with open(filepath, 'r', encoding='utf-8') as inputFile:
        urls = [line.strip() for line in inputFile.readlines()]
        urls = [line[:-1] if line.endswith(',') else line for line in urls]

    try:
        crawler: BaseMangaCrawler = None
        for idx, url in enumerate(urls):
            msg = f'----- Now downloading ({idx + 1}/{len(urls)}): {url} -----'
            console.info('-' * len(msg))
            console.info(msg)
            console.info('-' * len(msg))

            try:
                if url.startswith('https://manganelo.com'):
                    crawler = ManganeloCrawler(url, output)
                elif url.startswith('http://manga-panda.xyz'):
                    crawler = MangaPandaCrawler(url, output)

            except ValueError as err:
                console.error(str(err))

            crawler.numChapterThreads = cthreads
            crawler.numPageThreads = pthreads
            crawler.download()

    except KeyboardInterrupt:
        if crawler is not None:
            crawler.terminate()
            console.info('Keyboard interrupt detected. '
                         'Please wait while threads are terminated...')


def initializeLoggers():
    """
    Initialize the loggers.
    """
    # Set the global logging level to DEBUG
    logging.getLogger().setLevel(logging.DEBUG)

    # Disable 'noisy' libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('chardet').setLevel(logging.WARNING)

    initializeConsoleLogger()
    initializeFileLogger()


def initializeConsoleLogger():
    """
    Initialize the logger that will display logs to the console.
    """
    consoleHandler = logging.StreamHandler()

    # Set formatter to print only the message in console
    formatter = logging.Formatter('%(message)s')
    consoleHandler.setFormatter(formatter)

    # Set level to INFO
    consoleHandler.setLevel(logging.INFO)

    # Add the console handler to the root logger
    console.addHandler(consoleHandler)


def initializeFileLogger():
    """
    Initialize the logger that will log messages to a rotating log file.
    """
    # Create the log directory
    os.makedirs('./logs', exist_ok=True)

    maxBytes = 5_000_000
    backupCount = 5

    # Set the log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fileHandler = RotatingFileHandler('./logs/app.log', encoding='utf-8',
                                      maxBytes=maxBytes, backupCount=backupCount)
    fileHandler.setFormatter(formatter)

    # Set the log level to DEBUG so that everything will be written to the log file
    fileHandler.setLevel(logging.DEBUG)

    # Add the file handlser to the root logger
    logging.getLogger().addHandler(fileHandler)


initializeLoggers()

if __name__ == '__main__':
    try:
        parser = argh.ArghParser()
        parser.add_commands([download, manganelo, mangapanda])
        parser.dispatch()

    except Exception as err:  # pylint: disable=broad-except
        # Elegantly handle any unexpected exception
        logger.exception('An unexpected exception occurred, %s', err)
        console.error('An unexpected exception occurred. Program will terminate.')
