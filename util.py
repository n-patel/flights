from twilio.rest import TwilioRestClient

def init_loggers(filename):
    """ Return two loggers: (one that logs to file and console, one that logs to file only). """

    def file_log(message):
        filename.write(str(message) + '\n')

    def global_log(message):
        file_log(message)
        print(str(message))

    return (global_log, file_log)


def init_SMS_messenger(account_sid, auth_token, to_number, from_number):
    """ Return a function that sends an SMS message via Twilio. """

    def send_SMS(message):
        """ Send an SMS message using Twilio. """

        client = TwilioRestClient(account_sid, auth_token)
        client.messages.create(
            to    = to_number,
            from_ = from_number,
            body  = "New message:\n" + str(message)
        )

    return send_SMS


def parse_flights_from_file(file_name):
    flights = []
    currentFlight = {}

    def parse_line(line):
        nonlocal currentFlight

        if line == "":
            pass
        elif line.startswith('begin'):
            currentFlight = {}
        elif line.startswith('$'):
            currentFlight['budget'] = int(line.replace('$', ''))
        else:
            attribute, content = line.split(':')
            outbound, inbound = content.split('->')
            if outbound == ['']:
                outbound = []
            if inbound == ['']:
                inbound = []

            outboundItems, inboundItems = outbound.split(','), inbound.split(',')

            if attribute == 'airports':
                currentFlight['from'] = outboundItems
                currentFlight['to'] = inboundItems

            if attribute == 'dates':
                newFlight = currentFlight.copy()
                newFlight['leave'] = outboundItems
                newFlight['return'] = inboundItems
                flights.append(newFlight)

    with open(file_name, "r") as f:
        for line in f:
            parse_line(line.strip().replace(" ", ""))

    return flights
