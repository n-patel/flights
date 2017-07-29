from textwrap import dedent

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

    def get_roundtrips_in_budget(self, num=float('inf')):
        """ Returns a list of all RoundTrips in budget. """
        self.outgoing_flights.sort(key=lambda f: f.price)
        self.return_flights.sort(key=lambda f: f.price)

        roundtrips = []
        for out in self.outgoing_flights:
            for ret in self.return_flights:
                if out.price + ret.price <= self.budget and len(roundtrips) < num:
                    roundtrips.append( RoundTrip(out, ret) )
                else:
                    return roundtrips

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
