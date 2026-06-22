import csv
import os
import sys
import time
from datetime import datetime

import requests

# Define the API endpoint
BASE_URL = 'https://api-trestle.corelogic.com/trestle/odata/Property'

# Get token from IDX Exchange secure proxy instead of exposing CoreLogic credentials.
# The proxy key is read from the TRESTLE_PROXY_KEY env var and is intentionally NOT
# stored in this (public) repository. Set it before running:
#   export TRESTLE_PROXY_KEY=<your IDX Exchange proxy key>
_PROXY_KEY = os.environ.get('TRESTLE_PROXY_KEY')
if not _PROXY_KEY:
    raise SystemExit('TRESTLE_PROXY_KEY is not set. Export your IDX Exchange proxy key '
                     'before running (see README); it is not stored in this repo.')
AUTH_ENDPOINT = f'https://idxexchange.com/internal-api/trestle_token.php?key={_PROXY_KEY}'

# Months to extract if none are passed on the command line
DEFAULT_MONTHS = ['202602', '202603', '202604', '202605']

# Retry / backoff configuration for surviving dropped connections
MAX_RETRIES = 6
INITIAL_BACKOFF = 2.0      # seconds
BACKOFF_FACTOR = 2.0
MAX_BACKOFF = 60.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Column order for the output CSV (preserved exactly from the original script).
FIELDNAMES = [
    'OriginalListPrice', 'ListingKey', 'CloseDate', 'ClosePrice', 'ListAgentFirstName',
    'ListAgentLastName', 'Latitude', 'Longitude', 'UnparsedAddress', 'PropertyType',
    'LivingArea', 'ListPrice', 'DaysOnMarket', 'ListOfficeName', 'BuyerOfficeName',
    'CoListOfficeName', 'ListAgentFullName', 'CoListAgentFirstName', 'CoListAgentLastName',
    'BuyerAgentMlsId', 'BuyerAgentFirstName', 'BuyerAgentLastName', 'FireplacesTotal',
    'AssociationFeeFrequency', 'AboveGradeFinishedArea', 'ListingKeyNumeric', 'MLSAreaMajor',
    'TaxAnnualAmount', 'CountyOrParish', 'PropertyType', 'MlsStatus', 'ElementarySchool',
    'ListAgentFirstName', 'AttachedGarageYN', 'ParkingTotal', 'BuilderName', 'PropertySubType',
    'LotSizeAcres', 'SubdivisionName', 'BuyerOfficeAOR', 'YearBuilt', 'DaysOnMarket',
    'StreetNumberNumeric', 'LivingArea', 'ListingId', 'BathroomsTotalInteger', 'City',
    'TaxYear', 'BuildingAreaTotal', 'BedroomsTotal', 'ContractStatusChangeDate', 'Longitude',
    'ElementarySchoolDistrict', 'CoBuyerAgentFirstName', 'PurchaseContractDate',
    'ListingContractDate', 'BelowGradeFinishedArea', 'BusinessType', 'Latitude', 'ListPrice',
    'StateOrProvince', 'CoveredSpaces', 'MiddleOrJuniorSchool', 'FireplaceYN', 'Stories',
    'HighSchool', 'Levels', 'ListAgentLastName', 'CloseDate', 'LotSizeDimensions',
    'LotSizeArea', 'MainLevelBedrooms', 'NewConstructionYN', 'GarageSpaces', 'HighSchoolDistrict',
    'PostalCode', 'BuyerOfficeName', 'AssociationFee', 'LotSizeSquareFeet',
    'MiddleOrJuniorSchoolDistrict', 'UnparsedAddress',
]

# $select must list each field once; dict.fromkeys dedupes while keeping order.
SELECT_FIELDS = ','.join(dict.fromkeys(FIELDNAMES))


def parse_yyyymm(arg):
    """Validate a YYYYMM string and return (start, end) datetimes for that month."""
    if len(arg) != 6 or not arg.isdigit():
        raise ValueError(f"Expected a YYYYMM value (e.g. 202602), got {arg!r}")
    year, month = int(arg[:4]), int(arg[4:6])
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid month in {arg!r}")
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


def get_token():
    """Fetch a fresh bearer token from the IDX Exchange proxy."""
    resp = request_with_retry('GET', AUTH_ENDPOINT, timeout=30)
    resp.raise_for_status()
    token = resp.json().get('access_token')
    if not token:
        raise RuntimeError("Error retrieving token: access_token not found")
    return token


def request_with_retry(method, url, **kwargs):
    """Issue an HTTP request, retrying with exponential backoff on connection
    drops (incl. SSLEOFError) and transient server/rate-limit responses."""
    kwargs.setdefault('timeout', 60)
    backoff = INITIAL_BACKOFF
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code in RETRYABLE_STATUS:
                raise requests.HTTPError(
                    f"retryable status {resp.status_code}", response=resp)
            return resp
        # requests wraps SSLEOFError as requests.exceptions.SSLError; OSError
        # catches any raw ssl.SSLEOFError that slips through unwrapped.
        except (requests.exceptions.RequestException, OSError) as exc:
            last_exc = exc
            if attempt == MAX_RETRIES:
                break
            sleep_for = min(backoff, MAX_BACKOFF)
            print(f"[retry] {method} attempt {attempt}/{MAX_RETRIES} failed: "
                  f"{exc!r}; sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)
            backoff *= BACKOFF_FACTOR
    raise last_exc


def extract_month(yyyymm, token):
    """Pull all listing records for one YYYYMM into CRMLSListing<YYYYMM>.csv.
    Returns the (possibly refreshed) token."""
    start, end = parse_yyyymm(yyyymm)
    csv_file = f'CRMLSListing{yyyymm}.csv'
    headers = {'Authorization': f'Bearer {token}'}

    url = BASE_URL
    params = {
        '$select': SELECT_FIELDS,
        '$filter': (
            f"ListingContractDate ge {start.isoformat(timespec='milliseconds')}Z and "
            f"ListingContractDate lt {end.isoformat(timespec='milliseconds')}Z"
        ),
        '$top': 1000,
    }

    total_records = 0
    reauth_attempts = 0
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()

        while True:
            response = request_with_retry('GET', url, params=params, headers=headers)

            if response.status_code == 401 and reauth_attempts < 2:
                # Token expired mid-pull; refresh and retry the same page.
                reauth_attempts += 1
                print("[auth] token expired, refreshing...")
                token = get_token()
                headers = {'Authorization': f'Bearer {token}'}
                continue

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(f"Error Message: {response.text}")
                break

            data = response.json()
            for observation in data.get('value', []):
                writer.writerow({f: observation.get(f, '') for f in FIELDNAMES})
                total_records += 1

            # Follow server-side pagination until there are no more pages.
            if '@odata.nextLink' in data:
                url = data['@odata.nextLink']
                params = None  # nextLink already carries the full query string
            else:
                break

    print(f"Total {total_records} records exported to {csv_file}")
    return token


def main(argv):
    months = argv[1:] or DEFAULT_MONTHS
    # Validate all months up front so a typo fails before any network calls.
    for m in months:
        parse_yyyymm(m)

    token = get_token()
    for m in months:
        token = extract_month(m, token)


if __name__ == '__main__':
    main(sys.argv)
