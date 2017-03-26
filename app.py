import argparse
import configparser
import sys
import time
from collections import namedtuple
from textwrap import dedent
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from util import *

# Config data
CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
LOG_DATA         = CONFIG['data']['log_data'] == "true"
LOG_DIR          = CONFIG['data']['log_dir_path']
USE_PHANTOM_PATH = CONFIG['data']['use_custom_phantom_path'] == "true"
PHANTOM_PATH     = CONFIG['data']['phantom_path']
NUM_PASSENGERS   = CONFIG['data']['number_of_passengers']
SCRAPE_INTERVAL  = CONFIG['data']['scrape_interval']
ACCOUNT_SID      = CONFIG['twilio']['account_sid']
AUTH_TOKEN       = CONFIG['twilio']['auth_token']
FROM_NUMBER      = CONFIG['twilio']['from_number']
TO_NUMBER        = CONFIG['twilio']['to_number']


class Flight:
    """ Defines a Flight that holds a src airport, dest airport, date, and price. """

    def __init__(self, src, dst, date, price=float("inf")):
        self.src   = src
        self.dst   = dst
        self.date  = date
        self.price = price

    def set_price(self, price):
        self.price = price

    def __str__(self):
        string = "({date}) {src} -> {dst}".format(src=self.src,
                                                  dst=self.dst,
                                                  date=self.date)
        # display price field if populated
        if self.price != float("inf"):
            string += ": $" + str(self.price)

        return string


class RoundTrip:
    """ Defines a round-trip that holds an outbound and inbound Flight. """

    def __init__(self, outbound, inbound):
        self.outbound   = outbound
        self.inbound    = inbound
        self.total_cost = outbound.price + inbound.price

    def __str__(self):
        return dedent(
            """\
            Total cost: ${cost}
                {outbound}
                {inbound}\
            """
        ).format(
            cost     = self.total_cost,
            outbound = self.outbound,
            inbound  = self.inbound
        )


class Itinerary:
    """ Defines an Itinerary, which describes sources and destinations, begin and end dates, and a budget. """

    def __init__(self, src_airports, dst_airports, leave_dates, return_dates, budget):
        self.src_airports = src_airports
        self.dst_airports = dst_airports
        self.leave_dates  = leave_dates
        self.return_dates = return_dates
        self.budget       = budget

        self.outgoing_flights = []
        self.return_flights   = []

    def generate_outgoing_flights(self):
        """ Generates all outgoing flight possibilities. """
        flights = []
        for date in self.leave_dates:
            for src in self.src_airports:
                for dst in self.dst_airports:
                    flights.append( Flight(src, dst, date) )

        return flights

    def generate_return_flights(self):
        """ Generates all return flight possibilities. """
        flights = []
        for date in self.return_dates:
            for src in self.src_airports:
                for dst in self.dst_airports:
                    flights.append( Flight(dst, src, date) )

        return flights

    def get_best_roundtrip(self):
        """ Returns the cheapest RoundTrip. """
        out = min(self.outgoing_flights, key=lambda f: f.price)
        ret = min(self.return_flights,   key=lambda f: f.price)

        return RoundTrip(out, ret)

    def get_roundtrips_in_budget(self):
        """ Returns a list of all RoundTrips in budget. """
        roundtrips = []
        for out in self.outgoing_flights:
            for ret in self.return_flights:
                if out.price + ret.price <= self.budget:
                    roundtrips.append( RoundTrip(out, ret) )

        return roundtrips

    def is_in_budget(self, roundtrip):
        """ Returns whether a given RoundTrip is within budget. """
        return roundtrip.total_cost <= self.budget

    def reset_flights(self):
        """ Empties the arrays that hold flight costs. """
        self.outgoing_flights = []
        self.return_flights   = []

    def __str__(self):
        """
        Returns a string with all relevant Itinerary info.
            e.g. ["OAK", "SFO"] -> ["PHX"] from ["05/15", "05/16"] to ["05/20"] under $250
        """
        string = str(self.src_airports) + " -> " + str(self.dst_airports)
        string += " from " + str(self.leave_dates) + " to " + str(self.return_dates)
        string += " under $" + str(self.budget)

        return string

    def get_all_flights_string(self):
        """ Returns a string containing all flights stored within the Itinerary. """
        string = ""
        for f in self.outgoing_flights + self.return_flights:
            string += "\n    " + str(f)

        return string


def scrape_flight_prices(flight):
    """ Scrapes Southwest and returns an array of matching Flights (with populated price attributes). """
    if USE_PHANTOM_PATH:
        browser = webdriver.PhantomJS(PHANTOM_PATH)
    else:
        browser = webdriver.PhantomJS()
    browser.get("https://www.southwest.com/")

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


def scan(itineraries):
    """ Scan Southwest for all flights that could create full itineraries. """

    send_SMS = init_SMS_messenger(ACCOUNT_SID, AUTH_TOKEN, TO_NUMBER, FROM_NUMBER)

    while True:
        send_SMS("Starting scan... ({time})".format(time=datetime.now().strftime("%H:%M:%S")))

        for itin in itineraries:

            # Outgoing flights
            for flight in itin.generate_outgoing_flights():
                print("Scraping for " + str(flight))
                itin.outgoing_flights = scrape_flight_prices(flight)

            # Return flights
            # Use a dummy flight for one-way flights.
            # This will be overwritten in the loop if not one-way.
            itin.return_flights = [Flight("None", "None", "None", 0)]
            for flight in itin.generate_return_flights():
                print("Scraping for " + str(flight))
                itin.return_flights = scrape_flight_prices(flight)


            # Log all info to a file
            f = open(LOG_DIR + datetime.now().strftime("%Y.%m.%d.txt"), 'a+')
            log, file_log = init_loggers(f)

            log(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            log(itin)
            log("========= Best Round-trip: =========")
            log(itin.get_best_roundtrip())
            log("====================================")
            log("==== Round-trips within budget: ====")
            for r in itin.get_roundtrips_in_budget():
                log(r)
                send_SMS(r)
            if len(itin.get_roundtrips_in_budget()) == 0:
                log("None")
            log("====================================")

            # only log to file; don't spam console
            file_log("======= All flights: =======")
            file_log(itin.get_all_flights_string())
            file_log("\n============================\n")

            f.close()

        send_SMS("Finished scan at {time}".format(time=datetime.now().strftime("%H:%M:%S")))

        # Clean up and wait to scrape later
        for itin in itineraries:
            itin.reset_flights()
        time.sleep(int(SCRAPE_INTERVAL) * 60)


if __name__ == "__main__":
    to_phx  = [Itinerary(["OAK", "SFO"], ["PHX"], ["05/13", "05/14", "05/15", "05/16"], ["05/23", "05/24", "05/25", "05/26"], 200)]
    scan(to_phx)
