"""Webscrapes ulovdomov website"""
# pylint: disable=C0301,W1203
import sqlite3
import math
import logging
from typing import List
from datetime import datetime
from selenium import webdriver
from bs4 import BeautifulSoup


def scrape(
    crawler,
    rent: str,
    conditions: List[str],
    excluded_areas: List[str],
    areas: List[str],
    town: str = "temp",
):
    """Webscrapes Ulovdomov website"""
    # Create connection to database
    conn = sqlite3.connect(crawler.database)
    cursor = conn.cursor()
    try:
        # Create a new instance of the Chrome driver
        driver = webdriver.Chrome()
        # Variables
        counters = [0,0]
        base = "https://www.ulovdomov.cz"
        webpage= "ulovdomov"
        logging.critical("SCRAPING ULOVDOMOV")

        for area in areas:
            url = rent + area
            html_content = crawler.get_page_html(url,driver)
            soup = BeautifulSoup(html_content, "html.parser")
            logging.info(f"New page: {url}")
            print(url)

            listings = soup.find_all(attrs={"data-test": "watchDogSingleResult"})
            for listing in listings:  # for each listing
                ### Populate these variables ###
                title = listing.find(attrs={"data-test": "headingOfLeasesPreview"}).text.replace("m²", "")
                address = listing.find("p").text
                url = base + listing.find("a")['href']
                logging.info(f"Apartment listing: {url}")

                ### Extracts additional data from listing page  ###
                html_content = crawler.get_page_html(url,driver)
                with open("test2.html", "w", encoding="utf-8") as file:
                    file.write(html_content)
                soup = BeautifulSoup(html_content, "html.parser") 
                phone = "0000000000"
                description = soup.find(attrs={"data-test": "offerDetail.description"}).text

                table_name, apartment, apartment_num, state = crawler.data_validation(address, url, title, webpage, town, excluded_areas, conditions, phone, description=description) #TODO: Add optional parameters and add optional checks to main.py data_vaidation

                print(table_name)
                print(apartment)
                print(apartment_num)
                print(state)

                if state is False:
                    continue
                if apartment_num is False:
                    continue

                # table validation and data input
                counters, state = crawler.table_validation(conn, cursor, table_name, apartment, apartment_num,counters)

                logging.info(f"{counters[0]} new 1-Bedroom apartments added to google sheet")
                logging.info(f"{counters[0]} new 2-Bedroom apartments added to google sheet")

        cursor.close()
        logging.critical("END OF ULOVDOMOV")

    except KeyboardInterrupt:
        cursor.close()
        logging.critical("END OF ULOVDOMOV")
