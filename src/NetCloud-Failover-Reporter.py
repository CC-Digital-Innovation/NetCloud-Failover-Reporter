import configparser
import datetime
import os

import pandas as pd
import pytz
import requests
import time_uuid


# Module information.
__author__ = 'Anthony Farina'
__copyright__ = 'Copyright (C) 2022 Computacenter Digital Innovation'
__credits__ = ['Anthony Farina']
__maintainer__ = 'Anthony Farina'
__email__ = 'farinaanthony96@gmail.com'
__license__ = 'MIT'
__version__ = '2.0.0'
__status__ = 'Released'


# Configuration file variables for easy referencing.
CONFIG = configparser.ConfigParser()
CONFIG_PATH = '/../configs/NetCloud-Failover-Reporter-config.ini'
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG.read(SCRIPT_PATH + CONFIG_PATH)

# NetCloud API global variables.
NC_ALERT_API_URL = 'https://www.cradlepointecm.com/api/v2/alerts/'
NC_CP_API_ID = CONFIG['NetCloud API Info']['cp-api-id']
NC_CP_API_KEY = CONFIG['NetCloud API Info']['cp-api-key']
NC_ECM_API_ID = CONFIG['NetCloud API Info']['ecm-api-id']
NC_ECM_API_KEY = CONFIG['NetCloud API Info']['ecm-api-key']
NETCLOUD_HEADERS = {
    'X-CP-API-ID': NC_CP_API_ID,
    'X-CP-API-KEY': NC_CP_API_KEY,
    'X-ECM-API-ID': NC_ECM_API_ID,
    'X-ECM-API-KEY': NC_ECM_API_KEY,
    'Content-Type': 'application/json'
}

# Timeframe global variables.
USE_TIMEFRAMES = CONFIG['Timeframes'].getboolean('use-timeframes')
TIMEZONE = CONFIG['Timezone']['timezone']
# Check if the timeframe feature is being used.
if USE_TIMEFRAMES:
    # Represent days of the week in the timeframes as a list of ints.
    DAYS_OF_WEEK = \
        [int(i) for i in CONFIG['Timeframes']['days-of-week'].split(',')]
    # Get the start of the timeframe.
    START_HOUR = CONFIG['Timeframes'].getint('start-hour')
    START_MINUTE = CONFIG['Timeframes'].getint('start-minute')
    START_TIME = datetime.time(hour=START_HOUR, minute=START_MINUTE,
                               tzinfo=pytz.timezone(TIMEZONE))
    # Get the end of the timeframe.
    END_HOUR = CONFIG['Timeframes'].getint('end-hour')
    END_MINUTE = CONFIG['Timeframes'].getint('end-minute')
    END_TIME = datetime.time(hour=END_HOUR, minute=END_MINUTE,
                             tzinfo=pytz.timezone(TIMEZONE))

# Other global variables.
EXCEL_FILE_NAME = CONFIG['Output']['excel-file-name']
COL_LABELS = [
    'Router Name',
    'Router MAC Address',
    'Router Serial Number',
    'Failover Timestamp',
    'Failover Info'
]


# This method extracts all router failover events from NetCloud since
# the beginning of the month to the moment this method is run. The
# failover information is outputted to an Excel file which includes
# the router's name, MAC address, serial number, failover start time,
# and failover duration.
def netcloud_failover_reporter() -> None:
    # Get the current time in the relative timezone into a datetime
    # object.
    rel_now_dt = datetime.datetime.utcnow().replace(
        tzinfo=pytz.UTC).astimezone(pytz.timezone(TIMEZONE))

    # Get the start of the current month in the relative timezone in
    # UTC into a datetime object. (12:00 AM on the 1st of this month).
    rel_month_start_dt = datetime.datetime(
        rel_now_dt.year, rel_now_dt.month, 1, 0, 0, 0,
        tzinfo=rel_now_dt.tzinfo)
    rel_month_start_utc_dt = rel_month_start_dt.astimezone(
        pytz.timezone('UTC'))

    # Make a time UUID object for the relative UTC time for the start
    # of the month.
    rel_month_start_utc_tuuid = time_uuid.TimeUUID.convert(
        rel_month_start_utc_dt)

    # Extract the first batch of monthly failovers from NetCloud in
    # JSON format. A batch has a limit of 500 entries.
    failover_request = \
        requests.get(
            url=NC_ALERT_API_URL,
            params={
                'type': 'failover_event',
                'limit': '500',
                'created_at_timeuuid__gte': str(rel_month_start_utc_tuuid)
            },
            headers=NETCLOUD_HEADERS
        )
    monthly_failover_batch = failover_request.json()

    # Keep a reference to all the routers we have extracted
    # information for thus far.
    router_dict = dict()

    # Prepare the output list that will be converted to an Excel file.
    output_list = list()

    # Make a do-while condition to get more failovers if there are
    # multiple batches of failover alerts. Reminder: 1 batch = 500
    # failover alerts.
    next_failover_batch = True

    # Loop through all monthly failovers to find relevant failover
    # records to add to the output list.
    while next_failover_batch:
        # Loop through this batch's failovers to find relevant
        # failover records to add to the output list.
        for failover_record in monthly_failover_batch['data']:
            # Get the relative time this failover occurred at as a
            # datetime object.
            failover_time_utc = failover_record['friendly_info'].split(' ')[4]
            rel_time_dt = utc_to_timezone(
                failover_time_utc,
                '%Y-%m-%dT%H:%M:%S.%fZ.',
                TIMEZONE
            )

            # Check if timeframes are being used.
            if USE_TIMEFRAMES:
                # Prepare the logic to see if this record is relevant.
                in_timeframe = (
                    (START_TIME <= rel_time_dt.time() <= END_TIME)
                    and
                    (rel_time_dt.weekday() in DAYS_OF_WEEK)
                )

                # Check if this record is not in a configured
                # timeframe.
                if not in_timeframe:
                    # Move onto the next failover record.
                    continue

            # Prepare a list to contain relevant failover information.
            relevant_failover_record = list()

            # Extract the router number from the failover record.
            router_url = failover_record['router']
            router_url_split = router_url.split('/')
            router_num = router_url_split[len(router_url_split) - 2]

            # Check if the router exists in the router dictionary.
            if router_num not in router_dict:
                # Request router information from NetCloud.
                router_request = requests.get(url=router_url,
                                              headers=NETCLOUD_HEADERS)
                router_info = router_request.json()

                # Add router information to router dictionary.
                router_dict[router_num] = router_info

            # Add router information to relevant failover record. Add
            # or remove any lines needed to extract relevant
            # information.
            relevant_failover_record.append(router_dict[router_num]['name'])
            relevant_failover_record.append(router_dict[router_num]['mac'])
            relevant_failover_record.append(
                router_dict[router_num]['serial_number'])
            relevant_failover_record.append(datetime.datetime.strftime(
                rel_time_dt,
                '%m/%d/%Y %I:%M:%S %p ' + str(rel_time_dt.tzname()))
            )
            # Make the failover information look pretty.
            info_str_split = failover_record['friendly_info'].split('.')
            info_str = info_str_split[0][:-23] + '.' + info_str_split[2] + '.'
            relevant_failover_record.append(info_str)

            # Add the relevant failover record to the output list.
            output_list.append(relevant_failover_record)

        # Check if there is another batch of failover alerts to
        # process.
        if monthly_failover_batch['meta']['next'] is None:
            next_failover_batch = False
        else:
            # Extract the next batch of failovers from NetCloud in
            # JSON format.
            failover_request = \
                requests.get(url=monthly_failover_batch['meta']['next'],
                             headers=NETCLOUD_HEADERS)
            monthly_failover_batch = failover_request.json()

    # Convert the output list to an Excel file.
    output_dataframe = pd.DataFrame(output_list, columns=COL_LABELS)
    excel_title = './../reports/' + rel_now_dt.strftime('%Y-%m-') + \
                  EXCEL_FILE_NAME + '.xlsx'
    output_dataframe.to_excel(excel_title, index=None, header=True)


# Takes an arbitrarily formatted UTC time as a string and the format
# of the string (following Python's time formatting conventions) then
# converts it to the provided timezone. Returns a datetime object of
# the given time in the relative timezone (making it timezone-aware).
def utc_to_timezone(utc_str: str, utc_str_format: str, timezone: str) -> \
        datetime:
    # Convert the given time string to an unaware datetime object with
    # the given format.
    time_dt = datetime.datetime.strptime(utc_str, utc_str_format)

    # Make the datetime object aware by setting its timezone (UTC).
    time_utc_dt = time_dt.replace(tzinfo=pytz.UTC)

    # Convert the time in the datetime object from UTC to the provided
    # timezone.
    time_other_dt = time_utc_dt.astimezone(pytz.timezone(timezone))

    return time_other_dt


# Main method that runs the script. There is no input.
if __name__ == '__main__':
    # Check if the "reports" folder exists. If not, create it.
    if not os.path.isdir(SCRIPT_PATH + '/../reports'):
        os.mkdir(SCRIPT_PATH + '/../reports')

    # Run the script.
    netcloud_failover_reporter()
