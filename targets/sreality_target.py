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
        counter_1 = counter_2 = 0

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
                # checks white goods
                conditions_state = crawler.check_white_goods(conditions, description)
                # if no white goods
                if conditions_state[1] == 0:
                    logging.info("Apartment has no white goods")
                    continue
                # check updated date
                if not crawler.check_condition(update_date, updated_status):
                    logging.info("Apartment not updated recently")
                    continue
                # checks area
                if crawler.check_condition(excluded_areas, address):
                    logging.info("Apartment in bad area")
                    continue
                # get number of rooms
                apartment_num = crawler.get_number_of_rooms(
                    title
                )  # TODO: might be bugged must check it
                if apartment_num is False:
                    continue
                # add listing to database
                table_name = (
                    f"apartments_{apartment_num}_bedroom_{webpage}_{town.lower().strip()}"
                )
                apartment = [
                    address,
                    url,
                    conditions_state[0],
                    conditions_state[1],
                    phone,
                ]
                crawler.create_table(cursor, crawler.query[0], table_name)
                if (
                    crawler.insert_data(
                        conn, cursor, crawler.query[1], table_name, apartment
                    )
                    is False
                ):  # if listing in database skips adding it to google sheet
                    logging.info("Apartment already in table")
                    continue
                # counters
                if apartment_num == 1:
                    counter_1 += 1
                if apartment_num == 2:
                    counter_2 += 1
                # add data to google sheet
                crawler.add_to_google_sheet(
                    crawler.service_account,
                    crawler.spreadsheet_id,
                    apartment,
                    apartment_num,
                )
        logging.info(f"{counter_1} new 1-Bedroom apartments added to google sheet")
        logging.info(f"{counter_2} new 2-Bedroom apartments added to google sheet")

        driver.close()
        cursor.close()
        logging.critical("END OF  SREALITY")

    except KeyboardInterrupt:
        driver.close()
        cursor.close()
        logging.critical("END OF  SREALITY")
