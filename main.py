"""This script is used to scrape apartment listings from a variety of websites based in Czechia.
 It then saves them to a local database and to google sheet if all conditions are met.

 Author: Danny Kokkinos
 """

# pylint: disable=C0301,W1203
import time
import sqlite3
from typing import List
import logging
from pathlib import Path
from datetime import datetime
import gspread
import requests
from targets import sreality_target, bravis_target


class Crawler:
    """Creates a custom crawler used for apartment scraping"""

    def __init__(
        self, database: Path, queries: Path, service_account: str, spreadsheet_id: str
    ):
        self.database = database
        self.queries = queries
        self.service_account = service_account
        self.query: List[str]
        self.spreadsheet_id = spreadsheet_id
        # logging
        current_date = datetime.now().strftime("%d-%m")
        date = Path(f"logs/{current_date}.log")
        time_format = datetime.now().strftime("%H:%M")
        logging.basicConfig(
            filename=date,
            level=logging.INFO,
            format=f"{time_format} - %(levelname)s - %(message)s",
        )
        self.get_queries()

    # Supporting fucntions
    def get_queries(self):
        """Parses queries from queries.sql"""
        with open(self.queries, "r", encoding="UTF-8") as file:  # import SQL queries
            self.query = file.read().split(";")

    def get_page_html(self, url, driver=None):
        """gets the htmp page either by chrome driver or via direct request"""
        if driver is None:
            response = requests.get(url, timeout=5)
            time.sleep(2)
            if response.status_code == 200:
                return response.text
            else:
                logging.error(f"Request failed: {response.status_code}")
        driver.get(url)
        time.sleep(2)
        html_content = driver.page_source
        return html_content

    def check_white_goods(self, conditions, description):
        """Checks if specific white goods are present"""
        temp = []
        for condition in conditions:
            if condition.lower().replace(" ", "") in description.lower().replace(
                " ", ""
            ):
                temp.append(1)
            else:
                temp.append(0)
        return temp

    def check_condition(self, conditions, something):
        """Used to check specific conditions"""
        if conditions == []:  # used when dates are not restricted
            return True
        for condition in conditions:
            if condition.lower().replace(" ", "") in something.lower().replace(" ", ""):
                return True
        return False

    def get_number_of_rooms(self, title):
        """#determine which table to add it to"""
        title = title.replace(" ", "")
        if "2+kk" in title or "1+1" in title or "2+KT" in title:
            apartment_num = 1
        elif "3+kk" in title or "2+1" in title or "3+KT" in title:
            apartment_num = 2
        else:
            logging.info("Apartmen wrong number of bedrooms")
            return False
        return apartment_num

    def create_table(self, cursor, query, table_name):
        """Creates a table in the database if it doesn't already exist"""
        table = query.format(table_name)
        cursor.execute(table)  # Create table

    def insert_data(self, conn, cursor, query, table_name, data):
        """Inserts data into table"""
        query_formated = query.format(table_name)
        try:

            data = (
                data[0],  # address
                data[1],  # URL
                data[2],  # Condition 1
                data[3],  # Condition 2
                data[4],  # phone number
            )
            cursor.execute(query_formated, data)  # Insert data into table
            conn.commit()
            logging.info(f"Adding {data[0]} to {table_name}")
            return True
        except sqlite3.IntegrityError:
            return False

    def add_to_google_sheet(self, service_account, spreadshet_id, data, apartment_num):
        """Adds data to a google sheet"""
        gc = gspread.service_account(service_account)
        sheets = gc.open_by_key(spreadshet_id)
        worksheet = sheets.get_worksheet(apartment_num)
        row = len(worksheet.col_values(1)) + 1  # Get length of used rows

        # adds the date
        day = datetime.today().strftime("%d")
        month = datetime.today().strftime("%m")
        formated_date = f"{day}/{month}"

        hyperlink = f'=HYPERLINK("{data[1]}", "{data[0]}")'  # Add address and hyperlink
        row_data = [formated_date, hyperlink, "No", "No", "No", "No", ""]

        if data[2] == 1:
            row_data[2] = "Yes"
        if data[3] == 1:
            row_data[3] = "Yes"

        row_data.append(data[4])  # adds phone number
        worksheet.update(
            range_name=f"A{row}:H{row}",
            values=[row_data],
            value_input_option="user_entered",
        )  # Selects the list options
        logging.critical(
            f"Added listing to {apartment_num}_Bedroom_apartment in google sheet"
        )


if __name__ == "__main__":

    DATABASE = Path("database.db")
    QUERIES = Path("queries.sql")
    BAD_AREAS = [  # areas you want to exclude from your search
        "Zábrdovice",
        "Řečkovice",
        "Bystrc",
    ]
    SPREADSHEET_ID = "1v54j8oOHO9mchR_Akf05NE3WiLIEeosA9fnLOYQq3iw"  # spreadsheet ID can be found in the url
    SERVICE_ACCOUNT = "service_account.json"  # Service account token

    # creates a web crawler
    crawler = Crawler(DATABASE, QUERIES, SERVICE_ACCOUNT, SPREADSHEET_ID)
    # Sreality
    RENT = "https://www.sreality.cz/hledani/pronajem/byty?region=Brno&velikost=2%2Bkk,2%2B1,3%2Bkk&plocha-od=50&plocha-do=10000000000&cena-od=0&cena-do=23000&region-id=5740&region-typ=municipality&k-nastehovani=ihned"
    CONDITIONS = ["pračk", "myčk"]
    # update_date = ["Včera", "Dnes"]
    # Sreality
    # update_date = ["Dnes"]

    # sreality_target.scrape(
    #     crawler, RENT, CONDITIONS, BAD_AREAS, update_date, town="brno"
    # )

    # Bravis
    RENT = "https://www.bravis.cz/en/flats-for-rent?address=&typ-nemovitosti-byt+2=&typ-nemovitosti-byt+3=&action=search&mapa="
    CONDITIONS = ["washing machine", "dishwasher"]
    check_date = datetime(2024, 5, 1)  # Select Move in date
    bravis_target.scrape(crawler, RENT, CONDITIONS, BAD_AREAS, check_date, town="brno")
