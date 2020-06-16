import requests
import unidecode
from datetime import datetime
import locale
import re

api_url = "https://www.eventbriteapi.com/v3/"
def get_event(event_id, api_key):
    """
    Returns - Python dictionary with Eventbrite event's attributes
    """
    response = requests.get(
        "{}/events/{}/".format(api_url, event_id),
        headers = {
            "Authorization": "Bearer {}".format(api_key),
        },
        verify = True,
    )
    return response.json()


def get_venue(venue_id, api_key):
    response = requests.get(
        "{}/venues/{}/".format(api_url, venue_id),
        headers = {
            "Authorization": "Bearer {}".format(api_key),
        },
        verify = True,
    )
    return response.json()


def get_guests(event_id, api_key):
    """
    Returns - Python dictionary with Eventbrite attendees information
    """
    response = requests.get(
        "{}/events/{}/attendees/?status=attending".format(api_url, event_id),
        headers = { "Authorization": "Bearer {}".format(api_key), },
        verify = True,
    )

    guests = response.json()['attendees']

    # Check for any other pages of attendees
    while response.json()['pagination']['has_more_items']:
        continuation = response.json()['pagination']['continuation']
        response = requests.get(
            "{}/events/{}/attendees/?status=attending&continuation={}".format(api_url, event_id, continuation),
            headers = { "Authorization": "Bearer {}".format(api_key), },
            verify = True,
        )
        guests.extend(response.json()['attendees'])

    return guests


def safe_filename(filename):
    rules = {"!" : ".",
             "@" : "_at_",
             "#" : "_no_",
             "$" : "S",
             "%" : "_per_",
             "?" : ".",
             "&" : "_and_",
             "+" : "_and_",
             "*" : "_",
             "~" : "_in_",
             ";" : ".",
             ":" : ".",
             "," : ".",
             "/" : "-",
             "|" : "-",
             "\\": "-",
             " " : "_",
             "'" : "_",
             '"' : "_"    }

    filename = unidecode.unidecode(filename)

    for old, new in rules.items():
        filename = filename.replace(old, new)

    return filename.upper()


def safe_name(name):
    rules = {"&" : " and ",
             "\\": "/"    }

    for old, new in rules.items():
        name = name.replace(old, new)

    return name.upper()


def build_registrant_list(event, guests, title, date, duration, select, checked_in_only=True):
    """
    Returns - Python dictionary with formatted attendees information
    """
    if not title:
        title = re.sub("(\[.*\])", "", event['name']['text']).strip()

    if not duration:
        time_start = datetime.strptime(event['start']['local'], '%Y-%m-%dT%H:%M:%S')
        time_end   = datetime.strptime(event[ 'end' ]['local'], '%Y-%m-%dT%H:%M:%S')
        duration = (time_end - time_start).total_seconds() / 3600

    if not date:
        date = datetime.strptime(event['start']['local'], "%Y-%m-%dT%H:%M:%S")
        date = date.strftime("le %Y-%m-%d")

    # Separate column name and regex selection pattern
    col_regex = select.split('~', 1)
    col_name = col_regex[0]
    sel_pattern  = re.compile(col_regex[1])

    # set locale in french for month name
    locale.setlocale(locale.LC_ALL, 'fr_FR')

    filename_template = './certificates/Attestation_CQ_{}_{}_{}.pdf'
    attended_guests = []

    for guest in guests:
        checked_in_value = (not checked_in_only) or guest['checked_in']

        if checked_in_value and sel_pattern.search(str(guest[col_name])):
            first_name = guest['profile']['first_name']
            last_name = guest['profile']['last_name']
            email = guest['profile']['email']
            order_id = guest['order_id']
            context = {'workshop' : title, 
                       'first_name' : safe_name(first_name),
                       'last_name'  : safe_name(last_name),
                       'email' : email,
                       'date' : date,
                       'duration' : duration,
                       'order_id' : order_id,
                       'filename' : filename_template.format(safe_filename(first_name),
                                                             safe_filename(last_name),
                                                             order_id)
            }
            attended_guests.append(context)

    return attended_guests


