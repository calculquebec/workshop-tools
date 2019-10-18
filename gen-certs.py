# Copyright 2017-2019 Calcul Québec

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Developers and maintainers:
# - Félix-Antoine Fortin
# - Maxime Boissonneault
# - Pier-Luc St-Onge


import getpass
import locale
import os
import re
import smtplib
import sys

import cairosvg
import click
import click_config_file
import jinja2
import pandas
import requests
import unidecode
import yaml

from datetime import datetime
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

api_url = "https://www.eventbriteapi.com/v3/"

###############################################################################

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

###############################################################################

def get_guests(event_id, api_key):
    """
    Returns - Python dictionary with Eventbrite attendees information
    """
    response = requests.get(
        "{}/events/{}/attendees/".format(api_url, event_id),
        headers = { "Authorization": "Bearer {}".format(api_key), },
        verify = True,
    )

    guests = response.json()['attendees']

    # Check for any other pages of attendees
    while response.json()['pagination']['has_more_items']:
        continuation = response.json()['pagination']['continuation']
        response = requests.get(
            "{}/events/{}/attendees/?continuation={}".format(api_url, event_id, continuation),
            headers = { "Authorization": "Bearer {}".format(api_key), },
            verify = True,
        )
        guests.extend(response.json()['attendees'])

    return guests

###############################################################################

def csv_guests(csv_file):
    guests_df = pandas.read_csv(csv_file)
    guests_df.rename(columns={"First Name": "first_name",
                              "Last Name":  "last_name",
                              "Email":      "email"    }, inplace=True)
    status_col = 'Attendee Status'
    guests = []

    for index, row in guests_df.iterrows():
        guest = {'checked_in': row[status_col] == 'Checked In',
                 'order_id':   row['Order #'],
                 'profile':    row['first_name':status_col].to_dict(),
                 'answers':    row[status_col:].iloc[1:].to_dict()}
        guests.append(guest)

    return guests

###############################################################################

def safe_name(name):
    rules = {"&" : " and ",
             "\\": "/"    }

    for old, new in rules.items():
        name = name.replace(old, new)

    return name.upper()

###############################################################################

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

###############################################################################

def build_checkedin_list(event, guests, title, date, duration, select):
    """
    Returns - Python dictionary with formatted attendees information
    """
    if not title:
        title = re.sub("(\[.*\])", "", event['name']['text']).strip()

    if not duration:
        time_start = datetime.strptime(event['start']['local'], '%Y-%m-%dT%H:%M:%S')
        time_end   = datetime.strptime(event[ 'end' ]['local'], '%Y-%m-%dT%H:%M:%S')
        duration = (time_end - time_start).total_seconds() / 3600

    # Separate column name and regex selection pattern
    col_regex = select.split('~', 1)
    col_name = col_regex[0]
    sel_pattern  = re.compile(col_regex[1])

    # set locale in french for month name
    locale.setlocale(locale.LC_ALL, 'fr_FR')

    filename_template = './certificates/Attestation_CQ_{}_{}_{}.pdf'
    attended_guests = []

    for guest in guests:
        if guest['checked_in'] and (sel_pattern.search(str(guest[col_name]))):
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

###############################################################################

def write_certificates(guests, svg_tplt):
    """
    Generates one PDF per attendee
    """
    print("--- Generating PDFs ---")
    try:
        os.mkdir('./certificates')
    except OSError:
        pass

    # certificate jinja2 template
    tpl_dir = os.path.dirname(svg_tplt)
    tpl_name = os.path.basename(svg_tplt)
    tpl = jinja2.Environment(loader=jinja2.FileSystemLoader(tpl_dir)).get_template(tpl_name)

    for guest in guests:
        print(f"Generating: {guest['filename']}")
        cairosvg.svg2pdf(bytestring=tpl.render(guest).encode('utf-8'), 
                         write_to=guest['filename'])

###############################################################################

def create_email(gmail_user, guest, email_tplt, send_self):
    # Create email
    outer = MIMEMultipart()
    outer['From'] = gmail_user
    outer['To'] = gmail_user if send_self else guest['email']
    outer['Reply-to'] = email_tplt['replyto']
    outer['Subject'] = Header(email_tplt['subject'])

    # Attach body
    body = MIMEText(email_tplt['message'].format(**guest), 'plain')
    outer.attach(body)

    # Attach PDF Certificate
    msg = MIMEBase('application', "octet-stream")
    with open(guest['filename'], 'rb') as file_:
        msg.set_payload(file_.read())
    encoders.encode_base64(msg)
    msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(guest['filename']))
    outer.attach(msg)

    return outer

###############################################################################

def send_email(attended_guests, yml_tplt, send_self):
    email_tplt = {}
    with open(yml_tplt, 'rt', encoding='utf8') as f:
        email_tplt = yaml.load(f, Loader=yaml.FullLoader)

    gmail_user = input('gmail username: ')
    gmail_password = getpass.getpass('gmail password: ')

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(gmail_user, gmail_password)

        for guest in attended_guests:
            email = create_email(gmail_user, guest, email_tplt, send_self)

            # Send email
            if send_self:
                print('sending email to YOU about: {first_name} ({email})...'.format(**guest))
            else:
                print('sending email to: {first_name} {last_name} ({email})...'.format(**guest))

            try:
                server.sendmail(email['From'], email['To'], email.as_string())
            except smtplib.SMTPAuthenticationError as e:
                # If the GMail account is now allowing secure apps, the script will fail.
                # read : http://stackabuse.com/how-to-send-emails-with-gmail-using-python/
                print('Go to https://myaccount.google.com/lesssecureapps and Allow less secure apps.')
                sys.exit(1)

###############################################################################

class MainParams:
    def getAll(self):
        return (self.title,
                self.date,
                self.duration,
                self.select,
                self.svg_tplt,
                self.yml_tplt,
                self.send_atnd,
                self.send_self)

    def setAll(self, title, date, duration, select, svg_tplt, yml_tplt, send_atnd, send_self):
        self.title     = title
        self.date      = date
        self.duration  = duration
        self.select    = select
        self.svg_tplt  = svg_tplt
        self.yml_tplt  = yml_tplt
        self.send_atnd = send_atnd
        self.send_self = send_self

    def printParams(self):
        click.echo("--- Main Configuration ---")
        if self.title: click.echo(f"New title:  {self.title}")
        click.echo(f"Event date: {self.date}")
        click.echo(f"Duration:   {self.duration}")
        click.echo(f"Select if:  {self.select}")
        click.echo(f"SVG file:   {self.svg_tplt}")
        click.echo(f"YAML file:  {self.yml_tplt}")

###############################################################################

@click.group(invoke_without_command=False)
@click.option('--title',    help="(CQCG_TITLE) Override workshop title",   type=str, default=None)
@click.option('--date',     help="(CQCG_DATE) Specifiy the date manually", type=str)
@click.option('--duration', help="(CQCG_DURATION) Override workshop duration in hours", type=float, default=0)
@click.option('--select',   help="Column_name~Regex (select where ...)",   type=str, default="checked_in~True")
@click.option('--svg_tplt', help="(CQCG_SVG_TPLT) Certificate template",   type=click.Path())
@click.option('--yml_tplt', help="(CQCG_YML_TPLT) Email template",         type=click.Path())
@click.option('--send_atnd/--no-send_atnd', default=False, help="Send the certificate to each attendee")
@click.option('--send_self/--no-send_self', default=False, help="Send to yourself")
@click_config_file.configuration_option(default="config")
@click.pass_context
def main(ctx,      title, date, duration, select, svg_tplt, yml_tplt, send_atnd, send_self):
    ctx.obj.setAll(title, date, duration, select, svg_tplt, yml_tplt, send_atnd, send_self)

###############################################################################

@main.command()
@click.option('--event_id', help="(CQCG_FROMEB_EVENT_ID) Eventbrite Event ID", type=str)
@click.option('--api_key',  help="(CQCG_FROMEB_API_KEY) Eventbrite API Key",   type=str)
@click_config_file.configuration_option(default="config")
@click.pass_context
def fromeb(ctx, event_id, api_key):
    """ # Get data from the Eventbrite API """
    print("--- From Eventbrite ---")
    print(f"Event ID:   {event_id}")
    print(f"API KEY:    {api_key}")

    assert event_id, "The event ID is undefined"
    assert api_key,  "The API KEY is undefined"

    event = get_event(event_id, api_key)
    guests = get_guests(event_id, api_key)

    common_main(event, guests, ctx.obj)

###############################################################################

@main.command()
@click.option('--csv_file', help="(CQCG_FROMCSV_CSV_FILE) Eventbrite attendee summary in CSV", type=click.Path())
@click_config_file.configuration_option(default="config")
@click.pass_context
def fromcsv(ctx, csv_file):
    """ # Get data from a CSV file """
    print("--- From CSV File ---")
    print(f"CSV file:   {csv_file}")

    assert csv_file, "The CSV file is undefined"

    assert ctx.obj.title,    "The title is undefined"
    assert ctx.obj.date,     "The date is undefined"
    assert ctx.obj.duration, "The duration is undefined"

    event = {}
    guests = csv_guests(csv_file)

    common_main(event, guests, ctx.obj)

###############################################################################

def common_main(event, guests, params):
    params.printParams();
    title, date, duration, select, svg_tplt, yml_tplt, send_atnd, send_self = params.getAll()

    attended_guests = build_checkedin_list(event, guests, title, date, duration, select)
    write_certificates(attended_guests, svg_tplt)

    if send_atnd or send_self:
        send_email(attended_guests, yml_tplt, send_self)

###############################################################################

if __name__ == "__main__":
    main(auto_envvar_prefix='CQCG', obj=MainParams())
