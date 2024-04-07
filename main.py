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
from targets import sreality_target, bravis_target, foreigners_target, ulovdomov_target


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
    def data_validation(
        self,
        address,
        url,
        title,
        webpage,
        town,
        excluded_areas,
        conditions,
        phone,
        description="",
        update_date="",
        updated_status="",
        availability="",
        check_date="",
    ):
        """Validates data"""
        state = True
        # check if reserved
        if availability != "" and check_date != "":
            if "Reserved" in availability or "Pre-reserved" in availability:
                logging.info("Apartment Reserved")
                state = False
            # checks if its available after a specific date
            if state is True:
                temp = availability.replace("Available", "").replace(" ", "").split(".")
                date = datetime(int(temp[2]), int(temp[1]), int(temp[0]))
                if date < check_date:
                    logging.info("Apartment not available soon enough")
                    state = False
        # check updated date
        if update_date != "":
            if not self.check_condition(update_date, updated_status):
                logging.info("Apartment not updated recently")
                state = False
        # checks area
        if self.check_condition(excluded_areas, address):
            logging.info("Apartment in bad area")
            state = False
        # get number of rooms
        apartment_num = self.get_number_of_rooms(title)
        if apartment_num is False:
            state = False
        # checks white goods
        if description != "":
            conditions_state = self.check_white_goods(conditions, description)
        else:
            conditions_state = [2, 2]
        # if no white goods
        if conditions_state[1] == 0:
            logging.info("Apartment has no white goods")
            state = False
        # add listing to database
        table_name = (
            f"apartments_{apartment_num}_bedroom_{webpage}_{town.lower().strip()}"
        )
        apartment = [address, url, conditions_state[0], conditions_state[1], phone]
        return table_name, apartment, apartment_num, state

    def table_validation(
        self, conn, cursor, table_name, apartment, apartment_num, counters
    ):
        """Validates the data then adds to table and google sheet"""
        state = True
        self.create_table(cursor, self.query[0], table_name)
        if (
            self.insert_data(conn, cursor, self.query[1], table_name, apartment)
            is False
        ):  # if listing in database skips adding it to google sheet
            logging.info("Apartment already in table")
            state = False
        if state is True:
            if apartment_num == 1:
                counters[0] += 1
            elif apartment_num == 2:
                counters[1] += 1
            # add data to google sheet
            self.add_to_google_sheet(
                self.service_account,
                self.spreadsheet_id,
                apartment,
                apartment_num,
            )
        return counters, state

    def get_queries(self):
        """Parses queries from queries.sql"""
        with open(self.queries, "r", encoding="UTF-8") as file:  # import SQL queries
            self.query = file.read().split(";")

    def get_page_html(self, url, driver=None):
        """gets the htmp page either by chrome driver or via direct request"""
        if driver is None:
            response = requests.get(url, timeout=10)
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
            logging.critical(f"Adding {data[0]} to {table_name}")
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
        elif data[2] == 2:
            row_data[2] = "Maybe"
        if data[3] == 1:
            row_data[3] = "Yes"
        elif data[3] == 2:
            row_data[3] = "Maybe"

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
        "Řečkovice",
        "Bystrc",
        "Útěchov",
        "Adamov",
        "Veverská Bítýška"
    ]
    SPREADSHEET_ID = "1v54j8oOHO9mchR_Akf05NE3WiLIEeosA9fnLOYQq3iw"  # spreadsheet ID can be found in the url
    SERVICE_ACCOUNT = "service_account.json"  # Service account token

    # creates a web crawler
    crawler = Crawler(DATABASE, QUERIES, SERVICE_ACCOUNT, SPREADSHEET_ID)

    # Sreality
    RENT = "https://www.sreality.cz/hledani/pronajem/byty?region=Brno&velikost=2%2B1,3%2Bkk,2%2Bkk&plocha-od=50&plocha-do=10000000000&cena-od=15000&cena-do=27000&region-id=5740&region-typ=municipality"
    CONDITIONS = ["pračk", "myčk"]
    UPDATE_DATE = ["Včera", "Dnes"]
    # update_date = ["Dnes"]
    sreality_target.scrape(
        crawler, RENT, CONDITIONS, BAD_AREAS, update_date= UPDATE_DATE, town="brno"
    )

    # Bravis
    RENT = "https://www.bravis.cz/en/flats-for-rent?address=&typ-nemovitosti-byt+2=&typ-nemovitosti-byt+3=&action=search&mapa="
    CONDITIONS = ["washing machine", "dishwasher"]
    CHECK_DATE = datetime(2024, 5, 1)  # Select Move in date
    bravis_target.scrape(crawler, RENT, CONDITIONS, BAD_AREAS, CHECK_DATE, town="brno")

    # Foreigners
    RENT = "https://www.foreigners.cz/real-estate/apartment/rent/brno?size_from=50&location=m-0-582786-0&area=15&rooms%5B0%5D=2&rooms%5B1%5D=3&price_from=0&price_to=24000"
    CONDITIONS = ["washing machine", "dishwasher"]
    foreigners_target.scrape(crawler, RENT, CONDITIONS, BAD_AREAS, town="brno")

    # UlovDomov
    RENT = "https://www.ulovdomov.cz/pronajem/bytu/brno-stred/2-1?od=50m2&dispozice=2-kk%2C3-kk&lokace="
    CONDITIONS = ["pračk", "myčk"]
    SEARCH_AREAS = ["Staré Brno","Brno%2C%3BVeveří", "Brno%2C%3BPonava","Brno%2C%3BLíšeň", "Brno%2C%3BObřany", "Brno%2C%3BMaloměřice%3B", "Brno%2C%3BSlatina", "Brno-střed" ]
    ulovdomov_target.scrape(crawler, RENT, CONDITIONS, BAD_AREAS, SEARCH_AREAS, town="brno")
