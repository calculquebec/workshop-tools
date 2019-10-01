# Calcul Québec's Certificate Generator

## Installation
* On Compute Canada clusters only: `module load python/3.6.3`
* `virtualenv venv`
* `source venv/bin/activate`
* `pip install -r requirements.txt`

## Preparation
* On Eventbrite, make sure selected participants are "Checked In" in **Manage** > **Manage Attendees** > **Check-in**
* The script expects a `template.svg` file with the following template fields:
  - First name: `{{ first_name }}`
  - Last name: `{{ last_name }}`
  - Main title: `{{ workshop }}`
  - "le JJ mois AAAA": `{{ date }}`
  - Duration in hours: `{{ duration }}`
  - Order ID: `{{ order_id }}`
* For help and available options:  
  `python gen-certs.py --help`

## Execution examples
Make sure the Python virtual environment is loaded:
* To only generate PDFs:  
  `python gen-certs.py`
* To generate PDFs and send emails to YOU:  
  `python gen-certs.py --send_self`
* To generate PDFs and finally send emails to participants:  
  `python gen-certs.py --email`
