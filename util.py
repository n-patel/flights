from datetime import datetime
from twilio.rest import TwilioRestClient

def init_loggers(log_file):
    """ Return two loggers: (one that logs to file and console, one that logs to file only). """

    def file_log(message):
        log_file.write(str(message) + '\n')

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

        print("[%s] Text message sent!" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    return send_SMS
