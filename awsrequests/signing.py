from collections import OrderedDict
from copy import deepcopy
import datetime
import hashlib
import hmac
import sys

from requests.compat import (
    urlparse as url_parse, quote, unquote, urlencode, unquote_plus, quote_plus
)

_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

if is_py3:
    from urllib.parse import parse_qs
elif is_py2:  # fallback to Python 2
    from urlparse import parse_qs
    import urllib


#  Key derivation functions. See:
# http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'aws4_request')
    return kSigning


def get_headers_for_request(
    url, region, service, access_key, secret_key, session_token=None,
        payload='', headers={}, method='GET', t=None):
    # Create a date for headers and the credential string
    if not t:
        t = datetime.datetime.utcnow()
    amzdate = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')  # Date w/o time, used in credential scope

    # ************* TASK 1: CREATE A CANONICAL REQUEST *************
    # http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html

    # Step 1 is to define the verb (GET, POST, etc.)--already done.

    # Step 2: Create canonical URI--the part of the URI from domain to query
    # string (use '/' if no path)
    parsed = url_parse(url)
    host = parsed.netloc
    canonical_uri = quote(unquote_plus(parsed.path),
                          safe="!#$%&'()*+,/:;=?@[]~")

    # Step 3: Create the canonical query string. In this example (a GET request),
    # request parameters are in the query string. Query string values must
    # be URL-encoded (space=%20). The parameters must be sorted by name.
    # For this example, the query string is pre-formatted in the request_parameters variable.
    params = {}
    if parsed.query:
        pq = parse_qs(parsed.query).items()
        pq = [(p[0], sorted(p[1], key=lambda s: s.lower())) for p in pq]
        params = OrderedDict(sorted(pq, key=lambda s: s[0].lower()))

    if is_py2:
        # patch quote_plus aws sigv4 does not like escaped spaces with +
        qp_orig = deepcopy(urllib.quote_plus)
        urllib.quote_plus = quote
        canonical_querystring = urlencode(params, doseq=True)
        urllib.quote_plus = qp_orig
    else:
        canonical_querystring = urlencode(params, doseq=True, quote_via=quote)
    # bit hacky, but quote takes these out as urllib doesn't consider them safe
    canonical_querystring = canonical_querystring.replace('%7E', '~')

    # Step 4: Create the canonical headers and signed headers. Header names
    # and value must be trimmed and lowercase, and sorted in ASCII order.
    # Note that there is a trailing \n.
    canonical_headers = ''
    headers_to_sign = []
    _headers = {'host': host, 'x-amz-date': amzdate}
    _headers.update(deepcopy(headers))
    _headers = OrderedDict(
        sorted(_headers.items(), key=lambda s: s[0].lower()))
    for c in _headers:
        cv = c.strip().lower()
        val = ' '.join(_headers[c].split()).strip()
        if cv == 'x-amz-date':
            val = _headers[c]
        if c not in headers_to_sign:
            headers_to_sign.append(cv)
            canonical_headers = '{}{}:{}\n'.format(canonical_headers, cv, val)

    # Step 5: Create the list of signed headers. This lists the headers
    # in the canonical_headers list, delimited with ";" and in alpha order.
    # Note: The request can include any headers; canonical_headers and
    # signed_headers lists those that you want to be included in the
    # hash of the request. "Host" and "x-amz-date" are always required.
    signed_headers = ';'.join(headers_to_sign)

    # Step 6: Create payload hash (hash of the request body content). For GET
    # requests, the payload is an empty string ("").

    if payload is None:
        payload = ''
    # handle differences between library requests 2.11.0 and previous
    if type(payload) is bytes:
        payload_hash = hashlib.sha256(payload).hexdigest()
    else:
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # Step 7: Combine elements to create create canonical request
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + \
        '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash

    # ************* TASK 2: CREATE THE STRING TO SIGN*************
    # Match the algorithm to the hashing algorithm you use, either SHA-1 or
    # SHA-256 (recommended)
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = datestamp + '/' + region + \
        '/' + service + '/' + 'aws4_request'
    string_to_sign = algorithm + '\n' + amzdate + '\n' + credential_scope + \
        '\n' + hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    # ************* TASK 3: CALCULATE THE SIGNATURE *************
    # Create the signing key using the function defined above.
    signing_key = getSignatureKey(secret_key, datestamp, region, service)

    # Sign the string_to_sign using the signing_key
    signature = hmac.new(signing_key, (string_to_sign).encode(
        'utf-8'), hashlib.sha256).hexdigest()

    # ************* TASK 4: ADD SIGNING INFORMATION TO THE REQUEST *************
    # The signing information can be either in a query string value or in
    # a header named Authorization. This code shows how to use a header.
    # Create authorization header and add to request headers
    authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + \
        credential_scope + ', ' + 'SignedHeaders=' + \
        signed_headers + ', ' + 'Signature=' + signature

    # The request can include any headers, but MUST include "host", "x-amz-date",
    # and (for this scenario) "Authorization". "host" and "x-amz-date" must
    # be included in the canonical_headers and signed_headers, as noted
    # earlier. Order here is not significant.
    # Python note: The 'host' header is added automatically by the Python 'requests' library.
    headers_to_add = {'x-amz-date': amzdate,
                      'Authorization': authorization_header}

    if session_token:
        headers_to_add['X-Amz-Security-Token'] = session_token

    headers.update(headers_to_add)
    return headers
