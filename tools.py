# Copyright 2017-2019 Calcul Quebec

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
# - Felix-Antoine Fortin
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
import yaml

from datetime import datetime
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from eventbrite_functions import *

def update_usernames(guests, usernames=None):
    users = users if usernames else ["user%02d" % (i+1) for i in range(len(guests))]
    for guest,user in zip(guests,users):
        guest['username'] = user
    return guests

def csv_guests(csv_file):
    guests_df = pandas.read_csv(csv_file)
    guests_df.rename(columns={"First Name": "first_name",
                              "Last Name":  "last_name",
                              "Email":      "email"    }, inplace=True)
    status_col = 'Attendee Status'
    if not "Order #" in guests_df.columns:
        guests_df["Order #"] = ''

    if not "cancelled" in guests_df.columns:
        guests_df["cancelled"] = False

    if not status_col in guests_df.columns:
        guests_df[status_col] = 'Checked In'

    guests = []
    for index, row in guests_df.iterrows():
        guest = {'checked_in': row[status_col] == 'Checked In',
                 'order_id':   row['Order #'],
                 'cancelled':  row["cancelled"],
                 'profile':    row['first_name':status_col].to_dict(),
                 'answers':    row[status_col:].iloc[1:].to_dict()}
        guests.append(guest)

    return guests


def write_certificates(guests, certificate_svg_tplt):
    """
    Generates one PDF per attendee
    """
    print("--- Generating PDFs ---")
    try:
        os.mkdir('./certificates')
    except OSError:
        pass

    # certificate jinja2 template
    tpl_dir = os.path.dirname(certificate_svg_tplt)
    tpl_name = os.path.basename(certificate_svg_tplt)
    tpl = jinja2.Environment(loader=jinja2.FileSystemLoader(tpl_dir)).get_template(tpl_name)

    for guest in guests:
        print(f"Generating: {guest['filename']}")
        cairosvg.svg2pdf(bytestring=tpl.render(guest).encode('utf-8'), 
                         write_to=guest['filename'])

###############################################################################

def create_email(gmail_user, guest, email_tplt, send_self, attach_certificate=True, self_email=None):
    # Create email
    outer = MIMEMultipart()
    outer['From'] = gmail_user
    if send_self:
        if self_email:
            outer['To'] = self_email
        else:
            outer['To'] = gmail_user
    else:
        outer['To'] = guest['email']
    outer['Reply-to'] = email_tplt['replyto']
    outer['Subject'] = Header(email_tplt['subject'])

    # Attach body
    body = MIMEText(email_tplt['message'].format(**guest), 'plain')
    outer.attach(body)

    # Attach PDF Certificate
    if attach_certificate:
        msg = MIMEBase('application', "octet-stream")
        with open(guest['filename'], 'rb') as file_:
            msg.set_payload(file_.read())
        encoders.encode_base64(msg)
        msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(guest['filename']))
        outer.attach(msg)

    return outer

###############################################################################

def send_email(attended_guests, email_tplt_file, send_self, number_to_send, attach_certificate=True, gmail_user=None, gmail_password=None, self_email=None):
    email_tplt = {}
    with open(email_tplt_file, 'rt', encoding='utf8') as f:
        email_tplt = yaml.load(f, Loader=yaml.FullLoader)

    if not gmail_user:
        gmail_user = input('gmail username: ')
    if not gmail_password:
        gmail_password = getpass.getpass('gmail password: ')
    if not self_email:
        self_email = gmail_user

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(gmail_user, gmail_password)
        nsent = 0

        for guest in attended_guests:
            email = create_email(gmail_user, guest, email_tplt, send_self, attach_certificate, self_email)

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
            nsent = nsent + 1
            if nsent == number_to_send:
                break	
###############################################################################

class MainParams:
    def getAll(self):
        return (self.title,
                self.date,
                self.duration,
                self.select,
                self.certificate_svg_tplt,
                self.certificate_email_tplt,
                self.send_atnd,
                self.send_self,
		self.number_to_send,
                self.source,
                self.event_id,
                self.api_key,
                self.csv_file,
                self.gmail_user,
                self.gmail_password,
                self.self_email)

    def setAll(self, title, date, select, send_atnd, send_self, number_to_send, source, event_id, api_key, csv_file, gmail_user, gmail_password, self_email):
        self.title     = title
        self.date      = date
        self.select    = select
        self.send_atnd = send_atnd
        self.send_self = send_self
        self.number_to_send = number_to_send
        self.source    = source
        self.event_id  = event_id
        self.api_key   = api_key
        self.csv_file  = csv_file
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
        self.self_email = self_email
        self.duration   = None
        self.certificate_email_tplt = None
        self.certificate_svg_tplt = None
        self.username_email_tplt = None

    def printParams(self):
        click.echo("--- Main Configuration ---")
        if self.title: click.echo(f"New title:  {self.title}")
        click.echo(f"Event date: {self.date}")
        if self.duration: click.echo(f"Duration:   {self.duration}")
        click.echo(f"Select if:  {self.select}")
        if self.certificate_svg_tplt: click.echo(f"SVG file:   {self.certificate_svg_tplt}")
        if self.certificate_email_tplt: click.echo(f"YAML file:  {self.certificate_email_tplt}")
        if self.username_email_tplt: click.echo(f"YAML file:  {self.username_email_tplt}")

###############################################################################

@click.group(invoke_without_command=False)
@click.option('--title',    help="(WT_TITLE) Override workshop title",   type=str, default=None)
@click.option('--date',     help="(WT_DATE) Specifiy the date manually", type=str)
@click.option('--select',   help="Column_name~Regex (select where ...)", type=str, default="checked_in~True")
@click.option('--send_atnd/--no-send_atnd', default=False, help="Send the certificate to each attendee")
@click.option('--send_self/--no-send_self', default=False, help="Send to yourself")
@click.option('--number_to_send', help="Total number of certificates to send", type=int, default=-1)
@click.option('--source',   help="eventbrite|csv", default="eventbrite", type=str)
@click.option('--event_id', help="(WT_EVENT_ID) Eventbrite Event ID",    type=str)
@click.option('--api_key',  help="(WT_API_KEY) Eventbrite API Key",      type=str)
@click.option('--csv_file', help="(WT_CSV_FILE) Eventbrite attendee summary in CSV", type=click.Path())
@click.option('--gmail_user',      help="Gmail username",         type=str, default=None)
@click.option('--gmail_password',  help="Gmail password",         type=str, default=None)
@click.option('--self_email',      help="Email to send tests to", type=str, default=None)
@click_config_file.configuration_option(default="config")
@click.pass_context
def main(ctx,      title, date, select, send_atnd, send_self, number_to_send, source, event_id, api_key, csv_file, gmail_user, gmail_password, self_email):
    ctx.obj.setAll(title, date, select, send_atnd, send_self, number_to_send, source, event_id, api_key, csv_file, gmail_user, gmail_password, self_email)

###############################################################################

@main.command()
@click.option('--duration', help="(WT_CERTIFICATES_DURATION) Override workshop duration in hours", type=float, default=0)
@click.option('--certificate_svg_tplt',   help="(WT_CERTIFICATES_CERTIFICATE_SVG_TPLT) Certificate template", type=click.Path())
@click.option('--certificate_email_tplt', help="(WT_CERTIFICATES_CERTIFICATE_EMAIL_TPLT) Email template",     type=click.Path())
@click_config_file.configuration_option(default="config")
@click.pass_context
def certificates(ctx, duration, certificate_svg_tplt, certificate_email_tplt):
    ctx.obj.duration = duration
    ctx.obj.certificate_svg_tplt = certificate_svg_tplt
    ctx.obj.certificate_email_tplt = certificate_email_tplt
 
    ctx.obj.printParams();
    title, date, duration, select, certificate_svg_tplt, certificate_email_tplt, send_atnd, send_self, number_to_send, source, event_id, api_key, csv_file, gmail_user, gmail_password, self_email  = ctx.obj.getAll()

    if ctx.obj.source == "eventbrite":
        assert ctx.obj.event_id, "The event ID is undefined"
        assert ctx.obj.api_key,  "The API KEY is undefined"
        event_id = ctx.obj.event_id
        api_key  = ctx.obj.api_key

        """ # Get data from the Eventbrite API """
        print("--- From Eventbrite ---")
        print(f"Event ID:   {event_id}")
        print(f"API KEY:    {api_key}")


        event = get_event(event_id, api_key)
        guests = get_guests(event_id, api_key)
    elif ctx.obj.source == "csv":
        assert ctx.obj.csv_file, "The CSV file is undefined"
        assert ctx.obj.title,    "The title is undefined"
        assert ctx.obj.date,     "The date is undefined"
        assert ctx.obj.duration, "The duration is undefined"

        csv_file = ctx.obj.csv_file
        """ # Get data from a CSV file """
        print("--- From CSV File ---")
        print(f"CSV file:   {csv_file}")


        event = {}
        guests = csv_guests(csv_file)

    attended_guests = build_registrant_list(event, guests, title, date, duration, select, checked_in_only=True)
    write_certificates(attended_guests, certificate_svg_tplt)

    if send_atnd or send_self:
        send_email(attended_guests, certificate_email_tplt, send_self, number_to_send, attach_certificate=True, gmail_user=gmail_user, gmail_password=gmail_password, self_email=self_email)

###############################################################################

@main.command()
@click.option('--username_email_tplt', help="(WT_USERNAMES_USERNAME_EMAIL_TPLT) Email template", type=click.Path())
@click_config_file.configuration_option(default="config")
@click.pass_context
def usernames(ctx, username_email_tplt):
    ctx.obj.username_email_tplt = username_email_tplt
    ctx.obj.select = "cancelled~False"

    ctx.obj.printParams();
    title, date, duration, select, certificate_svg_tplt, certificate_email_tplt, send_atnd, send_self, number_to_send, source, event_id, api_key, csv_file, gmail_user, gmail_password, self_email  = ctx.obj.getAll()

    if ctx.obj.source == "eventbrite":
        assert ctx.obj.event_id, "The event ID is undefined"
        assert ctx.obj.api_key,  "The API KEY is undefined"
        event_id = ctx.obj.event_id
        api_key  = ctx.obj.api_key

        """ # Get data from the Eventbrite API """
        print("--- From Eventbrite ---")
        print(f"Event ID:   {event_id}")
        print(f"API KEY:    {api_key}")


        event = get_event(event_id, api_key)
        guests = get_guests(event_id, api_key)
    elif ctx.obj.source == "csv":
        assert ctx.obj.csv_file, "The CSV file is undefined"
        assert ctx.obj.title,    "The title is undefined"
        assert ctx.obj.date,     "The date is undefined"

        csv_file = ctx.obj.csv_file
        """ # Get data from a CSV file """
        print("--- From CSV File ---")
        print(f"CSV file:   {csv_file}")


        event = {}
        guests = csv_guests(csv_file)

    guests = build_registrant_list(event, guests, title, date, duration, select, checked_in_only=False)
    guests = update_usernames(guests)

    if send_atnd or send_self:
        send_email(guests, username_email_tplt, send_self, number_to_send, attach_certificate=False, gmail_user=gmail_user, gmail_password=gmail_password, self_email=self_email)
    else:
        for guest in guests:
            # Send email
            print('Not sending email to: {first_name} {last_name} ({email}), username:{username}...'.format(**guest))

###############################################################################

if __name__ == "__main__":
    main(auto_envvar_prefix='WT', obj=MainParams())
