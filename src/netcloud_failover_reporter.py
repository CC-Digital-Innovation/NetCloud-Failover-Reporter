import json
import os
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import dotenv
import pandas as pd
import pytz
import requests
from loguru import logger


# ====================== Environment / Global Variables =======================
dotenv.load_dotenv(override=True)

# Initialize customer constant global variables.
with open('/vault/secrets/nc_fail', 'r') as file:
    CUSTOMER_CONFIGS_FILE_JSON = json.load(file)
CUSTOMER_CONFIGS_STRING = CUSTOMER_CONFIGS_FILE_JSON['data']['customer_configs']
CUSTOMER_CONFIGS = json.loads(CUSTOMER_CONFIGS_STRING)

# Initialize Email API constant global variables.
EMAIL_API_BASE_URL = os.getenv('EMAIL_API_BASE_URL')
EMAIL_API_KEY = os.getenv('EMAIL_API_TOKEN')

# Initialize NetCloud constant global variables.
NETCLOUD_BASE_API_URL = 'https://www.cradlepointecm.com/api/v2'
NETCLOUD_API_MAX_LIMIT = 100

# Initialize other constant global variables.
REPORTING_INBOX = os.getenv('REPORTING_INBOX')
CSV_BASE_FILE_NAME = 'netcloud_failover_report'
REPORT_TIME_FORMAT = '%m/%d/%Y %I:%M:%S %p %Z'
REPORT_COLUMN_LABELS = [
    'Router Name',
    'Router MAC Address',
    'Router Serial Number',
    'Failover Timestamp',
    'Failover Info'
]
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


# ================================== Classes ==================================
class NetCloudFailoverAlert:
    """
    Represents a failover alert from the NetCloud API.
    """
    
    def __init__(self, **kwargs):
        """
        Initializes the failover alert's created at datetime, the friendly
        info, and the router number associated with this failover alert.
        
        Format of kwargs:
        {
            'friendly_info': str,
            'router': str
        }
        """
        
        # Extract the first sentence from the failover alert's "friendly_info"
        # field that contains the datetime string.
        failover_info_first_sentence = kwargs['friendly_info'].split('. ')[0]
        
        # Extract just the datetime string from the first sentence.
        failover_info_datetime_str = failover_info_first_sentence.split(' ')[-1]
        
        # Convert the datetime string to a datetime object in UTC.
        failover_datetime_utc = datetime.fromisoformat(failover_info_datetime_str)
        
        self.created_at_utc = failover_datetime_utc
        
        # Format the "failover_info" field to make it look pretty.
        failover_info_str_split = kwargs['friendly_info'].split('.')
        failover_info_str = f'{failover_info_str_split[0][:-23]}.{failover_info_str_split[2]}.'
        
        self.failover_info = failover_info_str
        
        # Extract the router number from the failover alert's "router" field.
        router_url = kwargs['router']
        router_number = router_url.split('/')[-2]
        
        self.router_number = router_number


class NetCloudRouter:
    """
    Represents a router in NetCloud.
    """
    
    def __init__(self, **kwargs):
        """
        Initializes the router's name, MAC address, and serial number.
        
        Format of kwargs:
        {
            'name': str,
            'mac': str,
            'serial_number': str
        }
        """
        
        self.name = kwargs['name']
        self.mac_address = kwargs['mac']
        self.serial_number = kwargs['serial_number']


# ================================= Functions =================================
def create_netcloud_api_headers(customer_netcloud_api_info: dict[str, str]) -> dict[str, str]:
    """
    Creates a header dictionary using the provided NetCloud API info found
    inside the customer config for making calls to the NetCloud API.

    Args:
        customer_netcloud_api_info (dict[str, str]): The NetCloud API info for
            this customer.

    Returns:
        dict[str, str]: The header dictionary for making calls to the NetCloud
            API.
    """
    
    # Create the headers for the NetCloud request payload for this customer.
    netcloud_cp_api_id = customer_netcloud_api_info['cp_api_id']
    netcloud_cp_api_key = customer_netcloud_api_info['cp_api_key']
    netcloud_ecm_api_id = customer_netcloud_api_info['ecm_api_id']
    netcloud_ecm_api_key = customer_netcloud_api_info['ecm_api_key']
    
    netcloud_api_headers = {
        'X-CP-API-ID': netcloud_cp_api_id,
        'X-CP-API-KEY': netcloud_cp_api_key,
        'X-ECM-API-ID': netcloud_ecm_api_id,
        'X-ECM-API-KEY': netcloud_ecm_api_key,
        'Content-Type': 'application/json'
    }
    
    # Return the NetCloud API headers.
    return netcloud_api_headers


def get_all_netcloud_failovers_since_last_month(customer_config: dict) -> list[NetCloudFailoverAlert]:
    """
    Gathers and returns all failover alerts for the provided customer since 5
    minutes before last month's beginning up until right now. This is to
    compensate for NetClouds true timestamp of when a failover occurred versus 
    what the "created_at" and "detected_at" fields in a failover alert returned 
    from the NetCloud API. This information is extracted from the
    "friendly_info" field and provides a more accurate timestamp of a failover 
    alert's occurrance.

    Args:
        customer_config (dict): The customer's config.

    Returns:
        list[NetCloudFailoverAlert]: The list of failover alerts since 5
            minutes before last month's beginning up until right now.
    """
    
    # Initialize the return list.
    all_failover_alerts = list[NetCloudFailoverAlert]()
    
    # Get the datetime 5 minutes before the beginning of last month in the
    # customer's timezone.
    today = datetime.today()
    customers_today = today.astimezone(pytz.timezone(customer_config['timezone']))
    customers_end_of_today = customers_today.replace(hour=23, minute=55, second=0, microsecond=0)
    customers_last_month_beginning = customers_end_of_today + relativedelta(day=31, months=-2)
    
    # Create the headers for the NetCloud API for this customer.
    netcloud_api_headers = create_netcloud_api_headers(customer_config['netcloud_api_info'])
    
    # Request for the first page of failover alerts from NetCloud.
    netcloud_failovers_raw_response = requests.get(
            url=f'{NETCLOUD_BASE_API_URL}/alerts/',
            params={
                'type': 'failover_event',
                'fields': 'friendly_info,router',
                'limit': NETCLOUD_API_MAX_LIMIT,
                'created_at__gt': customers_last_month_beginning.isoformat().replace('+', '%2b')
            },
            headers=netcloud_api_headers
    )
    netcloud_failovers_response = netcloud_failovers_raw_response.json()
    
    # Add the failovers to the returning list.
    all_failover_alerts.extend([NetCloudFailoverAlert(**failover_alert) for failover_alert in netcloud_failovers_response['data']])
    
    # Check if there is not another page of failovers to collect.
    next_page_of_failovers_url = netcloud_failovers_response['meta']['next']
    if not next_page_of_failovers_url:
        # Return the failovers we gathered since there are no more pages of
        # failover alerts to collect.
        return all_failover_alerts
    
    # Gather all failover alerts one page at a time from NetCloud.
    while next_page_of_failovers_url:
        # Request the next page of failover alerts from NetCloud.
        netcloud_failovers_raw_response = requests.get(
                url=next_page_of_failovers_url,
                headers=netcloud_api_headers
        )
        netcloud_failovers_response = netcloud_failovers_raw_response.json()
        
        # Add all the failover alerts from the response to the return list.
        all_failover_alerts.extend([NetCloudFailoverAlert(**failover_alert) for failover_alert in netcloud_failovers_response['data']])
        
        # Save the URL to the next page. Will be None if no URL exists.
        next_page_of_failovers_url = netcloud_failovers_response['meta']['next']
    
    # Return all the failover alerts.
    return all_failover_alerts


def is_in_customer_timeframe(failover_alert_utc_datetime: datetime, customer_config: dict) -> bool:
    """
    Checks if the provided UTC datetime (in ISO 8601 format) of a failover
    alert falls inside the provided customer's timeframe. Returns true if it
    does, false otherwise. A customer's timezone will always be used to
    calculate if the failover alert falls inside a timeframe or if it falls
    inside last month. If a customer is not using the timeframe feature, this
    function will return true if the failover alert falls inside last month,
    false otherwise.

    Args:
        failover_alert_utc_datetime (datetime): The failover alert's UTC
            datetime in ISO 8601 format.
        customer_config (dict): The customer config.

    Returns:
        bool: Returns true if the failover alert falls inside the customer's
            timeframe, false otherwise. If no timeframe is being used, returns
            true if the failover alert falls inside last month in the
            customer's timezone, false otherwise.
    """
    
    # Convert the datetime string into a datetime object in the customer's timezone.
    customer_timezone = customer_config['timezone']
    failover_alert_datetime = failover_alert_utc_datetime.astimezone(pytz.timezone(customer_timezone))
    is_in_last_month = failover_alert_datetime.month == (datetime.now() + relativedelta(months=-1)).month
    
    # Check if this customer is not using the timeframe feature.
    timeframe = customer_config['timeframe_info']
    if not timeframe:
        return is_in_last_month
    
    # Make the timeframe start / end times into time objects.
    timeframe_start = time.strptime(timeframe['start_time'], '%H:%M')
    failover_alert_time = time.strptime(f'{failover_alert_datetime.hour}:{failover_alert_datetime.minute}', '%H:%M')
    timeframe_end = time.strptime(timeframe['end_time'], '%H:%M')
    
    # Return whether this failover is in the customer's timeframe or not.
    return failover_alert_datetime.isoweekday() in timeframe['days_of_the_week'] and \
        (timeframe_start <= failover_alert_time <= timeframe_end) and \
        is_in_last_month


def filter_failovers_for_customer_timeframe(failover_alerts: list[NetCloudFailoverAlert], customer_config: dict) -> list[NetCloudFailoverAlert]:
    """
    Filters the provided failover alerts and returns only the failover alerts
    that fall under the provided customer's configured timeframe.

    Args:
        failover_alerts (list[NetCloudFailoverAlert]): The failover alerts to
            filter.
        customer_config (dict): The customer config.

    Returns:
        list[NetCloudFailoverAlert]: The failover alerts that fall inside the
            customer's timeframe.
    """
    
    # Create the returning list.
    filtered_failover_alerts = list[NetCloudFailoverAlert]()
    
    # For each alert, check if it falls into the customer's timeframe and add 
    # it to the returning list if so.
    for failover_alert in failover_alerts:
        # Check if this failover alert falls inside the provided customer's
        # configured timeframe. Add it to the filtered failover alerts if so.
        if is_in_customer_timeframe(failover_alert.created_at_utc, customer_config):
            filtered_failover_alerts.append(failover_alert)

    # Return the filtered failovers.
    return filtered_failover_alerts


def get_last_months_failover_alerts(customer_config: dict) -> list[dict]:
    """
    Gathers all of last month's failover alerts for a given customer and
    filters them based off a customer's configured timeframe. Returns a list of
    raw failover alerts.

    Args:
        customer_config (dict): The customer config.

    Returns:
        list[dict]: A filtered list of last month's failover events based off
            a customer's configured timeframe.
    """
    
    # Gather all failover alerts from the past month.
    last_months_failovers = get_all_netcloud_failovers_since_last_month(customer_config)

    # Filter to only get failover alerts that are in the customer's timeframe.
    filtered_last_months_failovers = filter_failovers_for_customer_timeframe(last_months_failovers, customer_config)

    # Return the filtered failover alerts.
    return filtered_last_months_failovers


def format_failover_alerts(failover_alerts: list[NetCloudFailoverAlert], customer_config: dict) -> list[list[str]]:
    """
    Formats the provided raw failover alerts to look pretty for the CSV file
    report. Uses the customer's timezone to format the "Failover Timestamp" 
    column.

    Args:
        failover_alerts (list[NetCloudFailoverAlert]): The failover alerts to
            format.
        customer_config (dict): The customer config.

    Returns:
        list[list[str]]: A list of failover rows for the CSV file report.
    """
    
    # Create the returning list and a list of router information we gather
    # over time.
    netcloud_router_info = dict[str, NetCloudRouter]()  # Keys are the router's number.
    formatted_failover_alerts = list[str]()
    
    # Create the headers for the NetCloud API for this customer.
    netcloud_api_headers = create_netcloud_api_headers(customer_config['netcloud_api_info'])
    
    # For each failover alert, format its information for CSV rows.
    for failover_alert in failover_alerts:
        # Initialize the list that will hold this row's values.
        failover_alert_row = list[str]()

        # Check if the router does not exist in the router dictionary.
        if failover_alert.router_number not in netcloud_router_info.keys():
            # Request router information from NetCloud.
            netcloud_router_request = requests.get(
                url=f'{NETCLOUD_BASE_API_URL}/routers/{failover_alert.router_number}/',
                params={
                    'fields': 'name,mac,serial_number'
                },
                headers=netcloud_api_headers
            )
            router_info = netcloud_router_request.json()

            # Add router information to the router dictionary.
            netcloud_router_info[failover_alert.router_number] = NetCloudRouter(**router_info)

        # Add router information to the failover alert row.
        failover_alerts_router = netcloud_router_info[failover_alert.router_number]
        failover_alert_row.append(failover_alerts_router.name)
        failover_alert_row.append(failover_alerts_router.mac_address)
        failover_alert_row.append(failover_alerts_router.serial_number)
        
        # Format the "Failover Timestamp" value for the customer's timezone.
        failover_created_at_datetime = failover_alert.created_at_utc.astimezone(pytz.timezone(customer_config['timezone']))
        failover_created_at_str = datetime.strftime(failover_created_at_datetime, REPORT_TIME_FORMAT)
        failover_alert_row.append(failover_created_at_str)
        
        # Add the failover info to the failover alert row.
        failover_alert_row.append(failover_alert.failover_info)

        # Add the relevant failover record to the returning list.
        formatted_failover_alerts.append(failover_alert_row)
    
    # Return the rows of formatted failover alerts.
    return formatted_failover_alerts
    

def netcloud_failover_reporter(customer_config: dict) -> None:
    """
    Gathers and formats all relevant failover events from last month for the
    provided customer config. Puts the report data into a CSV file and will
    email the customer's configured recipients and the Digital Innovation
    reporting inbox with the CSV file. 

    Args:
        customer_config (dict): The customer configuration.
    """
    
    # Gather all relevant failover reports from last month for this customer.
    logger.info('Gathering last month''s failover events...')
    last_months_failover_alerts = get_last_months_failover_alerts(customer_config)
    
    # Format the failover alerts for the report.
    logger.info('Formatting failover events...')
    formated_failover_alerts = format_failover_alerts(last_months_failover_alerts, customer_config)
    
    # Create a CSV file of the data.
    logger.info('Generating a CSV file of failover events...')
    failover_report_dataframe = pd.DataFrame(formated_failover_alerts, columns=REPORT_COLUMN_LABELS)
    one_month_ago = datetime.now() + relativedelta(months=-1)
    failover_report_file_name = f'{one_month_ago.strftime('%Y-%m')}_{CSV_BASE_FILE_NAME}.csv'
    failover_report_path = f'{SCRIPT_PATH}/../reports/{failover_report_file_name}'
    failover_report_dataframe.to_csv(failover_report_path, index=None, header=True)

    # Send the CSV file to the customer and our reporting email inbox.
    logger.info('Emailing the CSV file of failover events...')
    
    # Make the list of email recipients. Always include the reporting inbox.
    email_to = list()
    email_to.append(REPORTING_INBOX)
    email_to.extend(customer_config['email_to'])
    
    # Send the failover report via email.
    email_response = requests.post(
        url=f'{EMAIL_API_BASE_URL}/emailReport/',
        data={
            'to': ', '.join(email_to),
            'subject': f'{customer_config['name']} Monthly Failover Report',
            'table_title': [f'{customer_config['name']} Montly Failover Report']
        },
        headers={
            'API_KEY': EMAIL_API_KEY
        },
        files=[('files', open(failover_report_path, 'rb'))]
    )
    
    # Check if the email was sent successfully or not.
    if email_response.ok:
        logger.info('Successfully emailed the failover report!')
    else:
        logger.error('An error occurred emailing the failover report')
        logger.error(f'Status code: {email_response.status_code}')
        logger.error(f'Reason: {email_response.reason}')


def main() -> None:
    """
    Runs the script for each customer in the config file.
    """
    
    # Check if the "reports" folder exists. If not, create it.
    if not os.path.isdir(SCRIPT_PATH + '/../reports'):
        os.mkdir(SCRIPT_PATH + '/../reports')
    
    logger.info('Starting the NetCloud failover reporter...')
    
    # For each customer, run the NetCloud failover reporter.
    for customer_config in CUSTOMER_CONFIGS:
        logger.info(f'Starting the NetCloud failover reporter for {customer_config['name']}...')
        
        netcloud_failover_reporter(customer_config)
        
        logger.info(f'NetCloud failover reporter for {customer_config['name']} has completed!')
    
    logger.info('NetCloud failover reporter completed!')


if __name__ == '__main__':
    main()
    