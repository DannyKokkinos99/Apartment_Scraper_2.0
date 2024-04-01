"""Webscrapes bravis website"""
# pylint: disable=C0301,W1203
import sqlite3
import math
import logging
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup


def scrape(
    crawler,
    rent: str,
    conditions: List[str],
    excluded_areas: List[str],
    check_date,
    town: str = "temp",
):
    """Webscrapes bravis website"""
    try:
        # Create connection to database
        conn = sqlite3.connect(crawler.database)
        cursor = conn.cursor()
        counters = [0,0]
        base = "https://www.bravis.cz/en/"
        webpage= "bravis"
        logging.critical("SCRAPING BRAVINS")
        html_content = crawler.get_page_html(rent)
        # get number of pages
        soup = BeautifulSoup(html_content, "html.parser")
        number_of_apartments = int(soup.find("li", class_="count").text.split(" ")[0])
        pages = math.ceil(number_of_apartments / 21)
        for page in range(1, pages + 1):  # for each page in pages
            url = rent + f"&s={page}-order-0"
            logging.info(f"New page: {url}")
            html_content = crawler.get_page_html(url)
            soup = BeautifulSoup(html_content, "html.parser")
            listing_span = soup.find("div", class_="itemslist")
            listings = listing_span.findAll("div", class_="item")
            for listing in listings:  # for each listing
                title = ""
                address = ""
                url = ""
                phone = ""
                description = ""
                title = listing.find("div", class_="desc").find("h1").text
                address = listing.find("span", class_="ico location s14").text
                url = base + listing.find("a")["href"]
                logging.info(f"Apartment listing: {url}")

                # Extracts additional data from listing page
                html_content = crawler.get_page_html(url)
                soup = BeautifulSoup(html_content, "html.parser")
                phone = (
                    soup.find("div", class_="broker")
                    .find("a")
                    .text.replace(" ", "")
                    .replace("+420", "")
                )
                description = soup.find("div", class_="desc").get_text(strip=True)
                availability = soup.find("div", class_="newgallery").text.strip()

                table_name, apartment, apartment_num, state = crawler.data_validation(address, url, title, webpage, town, excluded_areas, conditions, phone, description = description, availability=availability, check_date=check_date)

                if state is False:
                    continue
                if apartment_num is False:
                    continue
                # table validation and data input
                counters, state = crawler.table_validation(conn, cursor, table_name, apartment, apartment_num,counters)

        logging.info(f"{counters[0]} new 1-Bedroom apartments added to google sheet")
        logging.info(f"{counters[0]} new 2-Bedroom apartments added to google sheet")

        cursor.close()
        logging.critical("END OF BRAVIS")

    except KeyboardInterrupt:
        cursor.close()
        logging.critical("END OF BRAVIS")
