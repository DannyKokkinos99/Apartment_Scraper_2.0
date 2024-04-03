"""Webscrapes template website"""
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
    town: str = "temp",
):
    """Webscrapes bravis website"""
    try:
        # Create connection to database
        conn = sqlite3.connect(crawler.database)
        cursor = conn.cursor()
        # Variables
        counters = [0,0]
        base = "www.template.com" #TODO: add base website
        webpage= "template" #TODO: add webpage name
        logging.critical("SCRAPING TEMPLATE") #TODO: add webpage name
        html_content = crawler.get_page_html(rent)

        ### get number of pages ###
        pages = "Calculate it" #TODO: calculate the number of pages if needed otherwise set to 0



        for page in range(1, pages + 1):  # for each page in pages

            url = "URL" #base page url
            logging.info(f"New page: {url}")

            html_content = crawler.get_page_html(url)
            soup = BeautifulSoup(html_content, "html.parser")


            listings: List #TODO: Find the listings as an array 
            for listing in listings:  # for each listing
                ### Populate these variables ###

                title = "" #TODO: Find value
                address = "" #TODO: Find value
                url = "" #TODO: Find value
                phone = "" #TODO: Find value
                description = "" #TODO: Find value (Optional used for finding appliances)

                logging.info(f"Apartment listing: {url}")

                ### Extracts additional data from listing page  ###           

                table_name, apartment, apartment_num, state = crawler.data_validation(address, url, title, webpage, town, excluded_areas, conditions, phone) #TODO: Add optional parameters and add optional checks to main.py data_vaidation

                if state is False:
                    continue
                if apartment_num is False:
                    continue

                # table validation and data input
                counters, state = crawler.table_validation(conn, cursor, table_name, apartment, apartment_num,counters)

        logging.info(f"{counters[0]} new 1-Bedroom apartments added to google sheet")
        logging.info(f"{counters[0]} new 2-Bedroom apartments added to google sheet")

        cursor.close()
        logging.critical("END OF TEMPLATE")

    except KeyboardInterrupt:
        cursor.close()
        logging.critical("END OF TEMPLATE")
