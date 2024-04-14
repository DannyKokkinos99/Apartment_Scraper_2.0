"""Webscrapes foreigners website"""
# pylint: disable=C0301,W1203
import sqlite3
import logging
from typing import List
from bs4 import BeautifulSoup

def scrape(
    crawler,
    rent: str,
    conditions: List[str],
    excluded_areas: List[str],
    town: str = "temp",
):
    """Webscrapes foreigners website"""
    try:
        # Create a new instance of the Chrome driver
        # Create connection to database
        conn = sqlite3.connect(crawler.database)
        cursor = conn.cursor()
        counters = [0,0]
        base = "https://www.foreigners.cz"
        webpage= "foreigners"
        logging.critical("SCRAPING FOREIGNERS")
        # run selenium
        html_content = crawler.get_page_html(rent)
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        # get number of pages
        # soup = BeautifulSoup(html_content, "html.parser")
        pages = 1 #TODO: fix for variable number of pages in the future
        for page in range(1, pages + 1):  # for each page in pages
            url = rent #TODO: fix when pages added
            html_content = crawler.get_page_html(url)
            soup = BeautifulSoup(html_content, "html.parser")
            temp = soup.find('div', class_ = 'row')
            listings = temp.findAll('div', class_ = 'col-sm-12 col-md-6 estate-listing-item-container')
            listings.pop(0)
            for listing in listings:  # for each listing
                title = ""
                address = ""
                url = ""
                phone = ""
                url = base + listing.find("a")["href"]
                logging.info(f"Apartment listing: {url}")
                print(url)
                # Extracts additional data from listing page
                html_content = crawler.get_page_html(url)
                soup = BeautifulSoup(html_content, "html.parser")
                street = soup.findAll('td', class_ = "text-bold")[1].text
                region = soup.findAll('td', class_ = "text-bold")[2].text
                address = f'{street} - {region}'
                phone = soup.findAll('span', class_ = 'consultant-info')[2].text.replace('+420', '').replace(" ", "")
                temp = ''
                # weird issue with the gaps in the phone number
                for c in phone:
                    if '0' <= c <= '9':
                        temp += c
                phone = temp
                title = soup.find("h2", class_ = "nemovitost").text
                # data validation
                table_name, apartment, apartment_num, state = crawler.data_validation(address, url, title, webpage, town, excluded_areas, conditions, phone)
                if state is False:
                    continue
                if apartment_num is False:
                    continue
                # table validation and data input
                counters, state = crawler.table_validation(conn, cursor, table_name, apartment, apartment_num,counters)

        logging.info(f"{counters[0]} new 1-Bedroom apartments added to google sheet")
        logging.info(f"{counters[1]} new 2-Bedroom apartments added to google sheet")
        cursor.close()
        logging.critical("END OF FOREIGNERS")

    except KeyboardInterrupt:
        cursor.close()
        logging.critical("END OF FOREIGNERS")
