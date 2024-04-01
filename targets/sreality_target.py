"""Webscrapes sreality website"""
# pylint: disable=C0301,W1203
import sqlite3
import math
import logging
from typing import List
from selenium import webdriver
from bs4 import BeautifulSoup


def scrape(
    crawler,
    rent: str,
    conditions: str,
    excluded_areas: List[str],
    update_date: List[str],
    town: str = "temp",
):
    """Webscrapes sreality website"""
    try:
        base = "https://www.sreality.cz"
        webpage = "sreality"
        logging.critical("SCRAPING SREALITY")
        # Create a new instance of the Chrome driver
        driver = webdriver.Chrome()
        # Create connection to database
        conn = sqlite3.connect(crawler.database)
        cursor = conn.cursor()

        # run selenium
        html_content = crawler.get_page_html(rent, driver)
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        listings = soup.findAll("div", class_="property ng-scope")
        num_listings = int(soup.findAll("span", class_="numero ng-binding")[1].text)
        pages = math.ceil(num_listings / len(listings)) + 1
        counters = [0,0]

        for page in range(1, pages + 1):  # for each page in pages
            page_q = f"&strana={page}"
            url = rent + page_q
            logging.info(f"New page: {url}")
            html_content = crawler.get_page_html(url, driver)
            soup = BeautifulSoup(html_content, "html.parser")
            listings = soup.findAll("div", class_="property ng-scope")
            for listing in listings:  # for each listing
                title = ""
                address = ""
                url = ""
                phone = ""
                description = ""
                title = listing.find("span", class_="name ng-binding").text
                address = listing.find("span", class_="locality ng-binding").text
                url = base + listing.find("a")["href"]
                logging.info(f"Apartment listing: {url}")

                # Extracts data from listing page
                html_content = crawler.get_page_html(url, driver)
                soup = BeautifulSoup(html_content, "html.parser")
                temp = soup.findAll("strong", class_="param-value")[3].text
                lines = temp.split("\n")
                cleaned_lines = [line.strip() for line in lines if line.strip()]
                updated_status = "\n".join(cleaned_lines)
                phone = (
                    soup.find("div", class_="contacts")
                    .find("a", class_="value final ng-binding ng-hide")["href"]
                    .replace("tel:", "")
                    .replace("+420", "")
                )
                description = soup.find("div", class_="description ng-binding").text
                table_name, apartment, apartment_num, state = crawler.data_validation(address, url, title, webpage, town, excluded_areas, conditions, phone, update_date = update_date,  updated_status =  updated_status, description = description)

                if state is False:
                    continue
                if apartment_num is False:
                    continue
                # table validation and data input
                counters, state = crawler.table_validation(conn, cursor, table_name, apartment, apartment_num,counters)

        logging.info(f"{counters[0]} new 1-Bedroom apartments added to google sheet")
        logging.info(f"{counters[1]} new 2-Bedroom apartments added to google sheet")

        driver.close()
        cursor.close()
        logging.critical("END OF  SREALITY")

    except KeyboardInterrupt:
        driver.close()
        cursor.close()
        logging.critical("END OF  SREALITY")
