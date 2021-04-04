# **MangaCrawler v2**
A python script to crawl manga sites and download the manga.

By: _Jake Randolph Muncada_

#### **Why Version 2?**
The previous version wasn't very flexible in handling the differences of the various manga sites. 

Particularly, it was made with the assumption that a manga had multiple chapters and each chapter had multiple pages. It couldn't handle manga whose pages aren't organized into chapters.

Also, adding a new manga site scraper was complicated and time consuming.

I could have improved the previous version and implemented the desired functionality, but it was easier to build a new one from the ground up.

Version 2 improves upon the previous version by being more robust. It is easier to implement scrapers of other manga sites.

---

## **Installation:**

Install the following python modules:
- requests
- bs4 (BeautifulSoup)
- argh
- tqdm

These can be installed using the following pip command:

    pip3 install requests bs4 argh tqdm

---

## **Usage:**

**Basic usage:** 

1. Create a text file called `urls.txt` on the same directory as the script.
2. Put the URLs of the manga you want to download in the text file, one URL per line.
3. Run the script: `python -m mangacrawler download`
4. The downloaded manga will be saved in the `output` directory.

You can also display the usage documentation using the following command:

    python -m mangacrawler download --help

To terminate the script, press `Ctrl + C`, but remember to just press it once.

---

## **Notes:**

1. Application logs can be found in the `logs` directory.
2. There are still just a few manga sites that have been implemented. More to come later (maybe).
3. Some manga sites have bot/scraper detection, so these sites will be difficult (if not impossible) to scrape. It might be bypassed by spoofing the User-Agent header, but that functionality hasn't been implemented yet.
4. Some SPA (Single Page Application) manga sites are also dynamically loaded using JavaScript, so the server response contains only JavaScript which the browser uses to display the site. These kinds of sites are not supported by this MangaCrawler.
