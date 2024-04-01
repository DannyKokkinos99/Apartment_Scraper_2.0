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
        counter_1 = counter_2 = 0
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

                # if item is Reserved
                gallery = soup.find("div", class_="newgallery").text.strip()
                if "Reserved" in gallery or "Pre-reserved" in gallery:
                    logging.info("Apartment Reserved")
                    continue
                # checks if its available after a specific date
                temp = gallery.replace("Available", "").replace(" ", "").split(".")
                date = datetime(int(temp[2]), int(temp[1]), int(temp[0]))
                if date < check_date:
                    logging.info("Apartment not available soon enough")
                    continue
                # checks white goods
                conditions_state = crawler.check_white_goods(conditions, description)
                # if no white goods
                if conditions_state[1] == 0:
                    logging.info("Apartment has no white goods")
                    continue
                # checks area
                if crawler.check_condition(excluded_areas, address):
                    logging.info("Apartment in bad area")
                    continue
                # get number of rooms
                apartment_num = crawler.get_number_of_rooms(title)
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

        cursor.close()
        logging.critical("END OF BRAVIS")

    except KeyboardInterrupt:
        cursor.close()
        logging.critical("END OF BRAVIS")
