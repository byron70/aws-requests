import datetime
import json
import os
import requests

from awsrequests import AwsRequester
from awsrequests.signing import get_headers_for_request

AWS_ACCESS_KEY_ID = 'AKIDEXAMPLE'
AWS_SECRET_KEY = 'wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY'
API_REGION = 'us-west-2'
API_PATH = "https://znlmeqqrf5.execute-api.us-west-2.amazonaws.com/testing"
API_HEADERS = {
    'Accept': 'application/json',
    'Content-type': 'application/json',
}
DT = datetime.datetime(2015, 8, 30, 12, 36, 00)
DR = 'us-east-1'


def test_suite():
    p = 'tests/aws-sig-v4-test-suite'
    for d in next(os.walk(p))[1]:
        if d == 'normalize-path':
            continue
        print('------------------{}'.format(d))
        with open(
                '{0}/{1}/{1}.req'.format(p, d)) as f:
            with open(
                    '{0}/{1}/{1}.authz'.format(p, d)) as a:
                want = a.read().strip()
                c = f.readline().split(' ')
                method = c[0]
                path = c[1]
                qs = None
                if len(path.split('?')) > 1:
                    qs = path.split('?')[1]
                    path = path.split('?')[0]

                headers = {}
                last_header = ''
                sec_token = None
                body = ''
                for l in f:
                    ls = l.split(':')
                    if len(ls) == 2:
                        if ls[0].lower() == 'host':
                            host = ls[1].strip()
                            continue
                        if ls[0] == 'X-Amz-Date':
                            continue
                        if ls[0] == 'X-Amz-Security-Token':
                            sec_token = ls[1]
                        last_header = ls[0]
                        if ls[0] in headers:
                            headers[ls[0]] = '{},{}'.format(
                                headers[ls[0]], ls[1].strip())
                        else:
                            headers.update({ls[0]: ls[1].strip()})

                    if len(ls) == 1 and len(ls[0].strip()):
                        if last_header == 'Content-Length':
                            body = body + ls[0].strip()
                        elif last_header != '':
                            headers[last_header] = headers[last_header] + \
                                ',' + ls[0].strip()

                req = requests.Request(
                    method,
                    'http://{}{}'.format(host, path),
                    headers=headers,
                    params=qs,
                    data=body)
                prepped = req.prepare()
                got = get_headers_for_request(
                    prepped.url,
                    DR,
                    'service',
                    AWS_ACCESS_KEY_ID,
                    AWS_SECRET_KEY,
                    sec_token,
                    payload=prepped.body,
                    headers=headers,
                    method=prepped.method,
                    t=DT)
                assert got['Authorization'] == want
