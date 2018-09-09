import argparse
import configparser
import sys
import time
from collections import namedtuple
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from util import *
from classes import *

# Config data
CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
LOG_DIR          = CONFIG['data']['log_dir_path']
USE_PHANTOM_PATH = CONFIG['data']['use_custom_phantom_path'] == "true"
PHANTOM_PATH     = CONFIG['data']['phantom_path']
NUM_PASSENGERS   = CONFIG['data']['number_of_passengers']
SCRAPE_INTERVAL  = CONFIG['data']['scrape_interval']
MAX_SMS_PER_RUN  = CONFIG['data']['max_sms_per_run']
ACCOUNT_SID      = CONFIG['twilio']['account_sid']
AUTH_TOKEN       = CONFIG['twilio']['auth_token']
FROM_NUMBER      = CONFIG['twilio']['from_number']
TO_NUMBER        = CONFIG['twilio']['to_number']


def construct_itineraries():
    itineraries = []
    for d in parse_flights_from_file("flights.txt"):
        itin = Itinerary(d['from'], d['to'], d['leave'], d['return'], d['budget'])
        itineraries.append(itin)

    return itineraries


def scrape_flight_prices(flight):
    """ Scrapes the website and returns an array of matching Flights (with populated price attributes). """
    if USE_PHANTOM_PATH:
        browser = webdriver.PhantomJS(PHANTOM_PATH)
    else:
        browser = webdriver.PhantomJS()
    browser.get("https://www.REPLACE_ME.com/")

    # Webdriver might be too fast. Tell it to slow down.
    # wait = WebDriverWait(browser, 120)
    # wait.until(EC.element_to_be_clickable((By.ID, "faresOutbound")))

    # Set one-way flight.
    one_way_elem = browser.find_element_by_id("trip-type-one-way")
    one_way_elem.click()

    # Set the departing airport.
    depart_airport = browser.find_element_by_id("air-city-departure")
    depart_airport.send_keys(flight.src)

    # Set the arrival airport.
    arrive_airport = browser.find_element_by_id("air-city-arrival")
    arrive_airport.send_keys(flight.dst)

    # Set departure date.
    depart_date = browser.find_element_by_id("air-date-departure")
    depart_date.clear()
    depart_date.send_keys(flight.date)

    # Clear the readonly attribute from the element.
    passengers = browser.find_element_by_id("air-pax-count-adults")
    browser.execute_script("arguments[0].removeAttribute('readonly', 0);", passengers)
    passengers.click()
    passengers.clear()

    # Set passenger count.
    passengers.send_keys(NUM_PASSENGERS)
    passengers.click()

    # Search.
    search = browser.find_element_by_id("jb-booking-form-submit-button")
    search.click()

    outbound_fares = browser.find_element_by_id("faresOutbound")
    outbound_prices = outbound_fares.find_elements_by_class_name("product_price")

    flights = []
    for price in outbound_prices:
        price = int(price.text.replace("$", ""))
        flights.append( Flight(flight.src, flight.dst, flight.date, price) )

    return flights


def scan():
    """ Scan website for all flights that could create full itineraries. """
    send_SMS = init_SMS_messenger(ACCOUNT_SID, AUTH_TOKEN, TO_NUMBER, FROM_NUMBER)
    while True:
        send_SMS("Starting scan... ({time})".format(time=datetime.now().strftime("%H:%M:%S")))

        itineraries = construct_itineraries()
        for itin in itineraries:
            for flight in itin.generate_outgoing_flights():
                print("Scraping for " + str(flight))
                itin.outgoing_flights += scrape_flight_prices(flight)

            return_flights = itin.generate_return_flights()
            if not return_flights:
                itin.return_flights = [Flight("None", "None", "None", 0)]
            for flight in return_flights:
                print("Scraping for " + str(flight))
                itin.return_flights += scrape_flight_prices(flight)

            # Log all info to a file.
            f = open(LOG_DIR + datetime.now().strftime("%Y.%m.%d.txt"), 'a+')
            log, file_log = init_loggers(f)

            log(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            log(itin)
            log("========= Best roundtrip: =========")
            log(itin.get_best_roundtrip())
            log("====================================")
            log("==== Best roundtrips within budget: ====")
            trips_in_budget = itin.get_roundtrips_in_budget()
            for r in trips_in_budget:
                log(r)
                send_SMS(r)
            if not trips_in_budget:
                log("None")
            log("====================================")

            # Only log to file; don't spam console.
            file_log("======= All flights: =======")
            file_log(itin.get_all_flights_string())
            file_log("\n============================\n")

            f.close()

        # send_SMS("Finished scan at {time}".format(time=datetime.now().strftime("%H:%M:%S")))

        # Clean up and wait to scrape later.
        for itin in itineraries:
            itin.reset_flights()
        time.sleep(int(SCRAPE_INTERVAL) * 60)


if __name__ == "__main__":
    scan()
