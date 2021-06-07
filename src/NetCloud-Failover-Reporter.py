import configparser
from datetime import datetime
import os

import pandas as pd
import pytz
import requests
import time_uuid


# Module information.
__author__ = 'Anthony Farina'
__copyright__ = 'Copyright 2021, NetCloud Monthly Failover Reporter'
__credits__ = ['Anthony Farina']
__license__ = 'MIT'
__version__ = '1.1.2'
__maintainer__ = 'Anthony Farina'
__email__ = 'farinaanthony96@gmail.com'
__status__ = 'Released'


# Global variables from the config file for easy referencing.
CONFIG = configparser.ConfigParser()
CONFIG_PATH = '/../configs/NetCloud-Failover-Reporter-config.ini'
CONFIG.read(os.path.dirname(os.path.realpath(__file__)) + CONFIG_PATH)
NETCLOUD_HEADERS = CONFIG._sections['NetCloud API Info']
TIMEZONE = CONFIG['Timezone Info']['timezone']
EXCEL_FILE_NAME = CONFIG['Output Info']['excel-file-name']
COL_LABELS = CONFIG['Output Info']['column-labels'].split(',')


# This method extracts the current month's failover events from NetCloud. This
# information is outputted to an Excel file. The output can be customized
# from the config.ini file.
def netcloud_failover_reporter() -> None:
    # Create the base URL for one batch of failover alerts in NetCloud.
    # NetCloud's maximum number of failover events from one HTTP GET call is
    # 500, so 1 batch = 500 failover alerts.
    failovers_url = 'https://www.cradlepointecm.com/api/v2/alerts/?type' \
                    '=failover_event&limit=500'

    # Get the current time in the relative timezone into a datetime object.
    rel_now_dt = datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(
        pytz.timezone(TIMEZONE))

    # Get the start of the current month in the relative timezone in UTC into
    # a datetime object.
    rel_month_start_dt = datetime(rel_now_dt.year, rel_now_dt.month, 1, 0,
                                  0, 0, tzinfo=rel_now_dt.tzinfo)
    rel_month_start_utc_dt = rel_month_start_dt.astimezone(pytz.timezone(
        'UTC'))

    # Make a time UUID object for the relative UTC time for the start of the
    # month.
    rel_month_start_utc_tuuid = time_uuid.TimeUUID.convert(
        rel_month_start_utc_dt)

    # Modify the base failover URL to only include failovers from the start
    # of the current month to now.
    failovers_url += '&created_at_timeuuid__gte=' + str(
        rel_month_start_utc_tuuid)

    # Extract the first batch of monthly failovers from NetCloud in JSON
    # format.
    failover_request = requests.get(url=failovers_url,
                                    headers=NETCLOUD_HEADERS)
    monthly_failover_batch = failover_request.json()

    # Keep a reference to all the routers we have extracted information for
    # thus far.
    router_dict = dict()

    # Prepare the output list that will be converted to an Excel file.
    output_list = list()

    # Make a do-while condition to get more failovers if there multiple
    # batches of failover alerts. Reminder: 1 batch = 500 failover alerts.
    next_failover_batch = True

    # Loop through all monthly failovers to find relevant failover records
    # to add to the output list.
    while next_failover_batch:
        # Loop through this batch's failovers to find relevant failover
        # records to add to the output list.
        for failover_record in monthly_failover_batch['data']:
            # Get the relative time this failover occurred at as a datetime
            # object.
            rel_time_dt = convert_utc(failover_record['created_at'],
                                      '%Y-%m-%dT%H:%M:%S.%f%z', TIMEZONE)

            # Prepare the logic to see if this record is relevant. If all
            # failovers should be extracted then leave this section alone.
            # example_cond_1 = rel_time_dt.weekday() != 5 or
            #                  rel_time_dt.weekday() != 6
            # example_cond_2 = rel_time_dt.hour >= 9 and rel_time_dt.hour <= 17

            # Check if this failover is relevant. If so, add it to the
            # output list. Uncomment if statement if there are conditions
            # made above.
            # if example_cond_1 and example_cond_2:
            # BEGIN IF-STATEMENT INDENTATION ---------------------------------
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

            # Add router information to relevant failover record. Add or remove
            # any lines needed to extract relevant information.
            relevant_failover_record.append(router_dict[router_num]['name'])
            relevant_failover_record.append(router_dict[router_num]['mac'])
            relevant_failover_record.append(router_dict[router_num][
                                                'serial_number'])
            relevant_failover_record.append(datetime.strftime(
                rel_time_dt, '%m/%d/%Y %I:%M:%S %p ' +
                             str(rel_time_dt.tzname())))
            relevant_failover_record.append(failover_record['type'])

            # Add the relevant failover record to the output list.
            output_list.append(relevant_failover_record)
            # END IF-STATEMENT INDENTATION -----------------------------------

        # Check if there is another batch of failover alerts to process.
        if monthly_failover_batch['meta']['next'] is None:
            next_failover_batch = False
        else:
            # Extract the next batch of failovers from NetCloud in JSON format.
            failovers_url = monthly_failover_batch['meta']['next']
            failover_request = requests.get(url=failovers_url,
                                            headers=NETCLOUD_HEADERS)
            monthly_failover_batch = failover_request.json()

    # Convert the output list to an Excel file.
    output_dataframe = pd.DataFrame(output_list, columns=COL_LABELS)
    output_dataframe.to_excel('./../' + EXCEL_FILE_NAME + '.xlsx', index=None,
                              header=True)


# Takes an arbitrarily formatted UTC time as a string and the format of
# the string (following Python's time formatting conventions) then converts
# it to the provided timezone. Returns a datetime object of the given time in
# the relative timezone (timezone-aware).
def convert_utc(utc_str: str, utc_str_format: str, timezone: str) -> datetime:
    # Convert the given time string to an unaware datetime object with
    # the given format.
    time_dt = datetime.strptime(utc_str, utc_str_format)

    # Make the datetime object aware by setting its timezone (UTC).
    time_utc_dt = time_dt.replace(tzinfo=pytz.UTC)

    # Convert the time in the datetime object from UTC to the provided
    # timezone.
    time_other_dt = time_utc_dt.astimezone(pytz.timezone(timezone))

    return time_other_dt


# The main method that runs the NetCloud failover reporter method.
# There is no input.
if __name__ == '__main__':
    # Run the script.
    netcloud_failover_reporter()
