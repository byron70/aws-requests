
from awsrequests import AwsRequester

API_REGION = 'us-west-2'
API_PATH = "https://znlmeqqrf5.execute-api.us-west-2.amazonaws.com/testing"
API_HEADERS = {
    'Accept': 'application/json',
    'Content-type': 'application/json',
}


def test_uri_path_with_trailing_space():
    req = AwsRequester(region=API_REGION)
    got = req.get(
        url='{}/pets/1234 '.format(API_PATH),
        params={'filters': '[["foo","eq","bar one "]]'},
        headers=API_HEADERS,
    )
    assert got.status_code == 200
