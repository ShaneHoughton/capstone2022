import os
import json
from functools import partial
from pytest import fixture, raises
import requests
import requests_mock
import mirrclient.client
from mirrclient.client import  NoJobsAvailableException, TempClient, Validator, ServerValidator
from mirrclient.client import is_environment_variables_present
# from mirrclient.client import execute_client_task
#from mirrclient.client import read_client_id


BASE_URL = 'http://work_server:8080'


@fixture(autouse=True)
def mock_env():
    os.environ['WORK_SERVER_HOSTNAME'] = 'work_server'
    os.environ['WORK_SERVER_PORT'] = '8080'
    os.environ['API_KEY'] = 'TESTING_KEY'


@fixture(name='mock_requests')
def fixture_mock_requests():
    return requests_mock.Mocker()


# def test_client_url():
#     client = Client()
#     assert client.url == BASE_URL


def test_check_all_env_values():
    assert is_environment_variables_present() is True


def test_check_no_env_values():
    # Need to delete env variables set by mock_env fixture
    del os.environ['WORK_SERVER_HOSTNAME']
    del os.environ['WORK_SERVER_PORT']
    del os.environ['API_KEY']
    assert is_environment_variables_present() is False


def test_check_no_hostname():
    # Need to delete hostname env variable set by mock_env fixture
    del os.environ['WORK_SERVER_HOSTNAME']
    assert is_environment_variables_present() is False


def test_check_no_server_port():
    # Need to delete server port env variable set by mock_env fixture
    del os.environ['WORK_SERVER_PORT']
    assert is_environment_variables_present() is False


def test_check_no_api_key():
    # Need to delete api key env variable set by mock_env fixture
    del os.environ['API_KEY']
    assert is_environment_variables_present() is False


def mock_assure_request(mocker):
    mocker.patch(
        'mirrclient.client.Client.get_job',
        side_effect=partial(mirrclient.client.assure_request, sleep_time=0)
    )


def mock_get_job(mocker):
    mocker.patch(
        'mirrclient.client.Client.get_job',
        return_value=None
    )


def mock_raise_connection_error(mocker):
    mocker.patch(
        'requests.get',
        side_effect=requests.exceptions.ConnectionError
    )


def read_mock_client_id(mocker, value):
    mocker.patch(
        'mirrclient.client.read_client_id',
        return_value=value
    )


def write_mock_client_id(mocker):
    mocker.patch(
        'mirrclient.client.Client.write_client_id',
        return_value=''
    )

######################################
# Refactoring tests

def test_tempclient_gets_job(mock_requests):
    server_validator = ServerValidator('http://test.com')
    client = TempClient(server_validator, None)
    with mock_requests:
        mock_requests.get(
            'http://test.com/get_job',
            json={'job': {'1': 1, 'job_type': 'attachments'}},
            status_code=200
        )
        job_info = client.get_job()
        assert ('1', 1, 'attachments') == job_info


def test_temp_client_throws_exception_when_no_jobs(mock_requests):
    server_validator = ServerValidator('http://test.com')
    client = TempClient(server_validator, None)
    with mock_requests:
        mock_requests.get(
            'http://test.com/get_job',
            json={'error': 'No jobs available'},
            status_code=403
        )

        with raises(NoJobsAvailableException):
            client.get_job()


def test_temp_client_gets_id_from_server(mock_requests):
    server_validator = ServerValidator('http://test.com')
    with mock_requests:
        mock_requests.get(
            'http://test.com/get_client_id',
            json={'client_id': 1},
            status_code=200
        )
        client = TempClient(server_validator, None)
        client.get_id()
        assert client.id == 1


def test_temp_client_gets_id_from_server(mock_requests):
    server_validator = ServerValidator('http://test.com')
    with mock_requests:
        mock_requests.get(
            'http://test.com/get_client_id',
            json={'client_id': 1},
            status_code=200
        )
        client = TempClient(server_validator, None)
        client.get_id()
        assert client.id == 1


def test_api_call_has_api_key2(mock_requests):
    validator = Validator()
    client = TempClient(None, validator)
    client.api_key = 'KEY12345'
    with mock_requests:
        mock_requests.get(
            'http://regulations.gov/job',
            json={'data': {'foo': 'bar'}},
            status_code=200
        )
        client.perform_job('http://regulations.gov/job')

        assert '?api_key=KEY12345' in mock_requests.request_history[0].url


def test_tempclient_performs_job(mock_requests):
    api_validator = Validator()
    server_validator = ServerValidator('http://test.com')
    client = TempClient(server_validator, api_validator)
    client.api_key = 1234
    
    with mock_requests:
        mock_requests.get(
            'http://test.com/get_job',
            json={'job': {'1': 'http://url.com', 'job_type': 'documents'}},
            status_code=200
        )
        mock_requests.get(
            'http://url.com?api_key=1234',
            json={'data': {'id': '1', 'attributes': {'agencyId': 'NOAA'},
                           'job_type': 'documents'}},
            status_code=200
        )
        mock_requests.put('http://test.com/put_results', text='{}')
        client.job_operation()

        put_request = mock_requests.request_history[2]
        print(put_request)
        json_data = json.loads(put_request.json())
        saved_data = json_data['results']['data']
        assert saved_data['attributes'] == {'agencyId': 'NOAA'}
        assert saved_data['id'] == '1'
        assert saved_data['job_type'] == 'documents'


def test_client_returns_403_error_to_server2(mock_requests):

    api_validator = Validator()
    server_validator = ServerValidator('http://test.com')
    client = TempClient(server_validator, api_validator)
    client.api_key = 1234

    with mock_requests:
        mock_requests.get(
            'http://test.com/get_job',
            json={'job': {'1': 'http://url.com', 'job_type': 'documents'}},
            status_code=200
        )

        regulation_response = {"errors": [{
            "status": "403",
            "title": "The document ID could not be found."}],
            "error": "API limit reached."
        }

        mock_requests.get(
            'http://url.com?api_key=1234',
            json=regulation_response,
            status_code=403
        )

        mock_requests.put(
            'http://test.com/put_results',
            json={'success': 'The job was successfully completed'},
            status_code=200
        )
        client.job_operation()
        response = mock_requests.request_history[-1]
        assert '403' in response.json()


def test_client_returns_400_error_to_server2(mock_requests, mocker):
    api_validator = Validator()
    server_validator = ServerValidator('http://test.com')
    client = TempClient(server_validator, api_validator)
    client.api_key = 1234

    with mock_requests:
        mock_requests.get(
            'http://test.com/get_job',
            json={'job': {'1': 'http://url.com', 'job_type': 'documents'}},
            status_code=200
        )

        regulation_response = {"errors": [{
            "status": "400",
            "title": "The document ID could not be found."}]}

        mock_requests.get(
            'http://url.com?api_key=1234',
            json=regulation_response,
            status_code=400
        )

        mock_requests.put(
            'http://test.com/put_results',
            json={'success': 'The job was successfully completed'},
            status_code=200
        )
        client.job_operation()
        response = mock_requests.request_history[-1]
        assert '400' in response.json()





def test_client_returns_400_error_to_server2(mock_requests, mocker):
    api_validator = Validator()
    server_validator = ServerValidator('http://test.com')
    client = TempClient(server_validator, api_validator)
    client.api_key = 1234

    with mock_requests:
        mock_requests.get(
            'http://test.com/get_job',
            json={'job': {'1': 'http://url.com', 'job_type': 'documents'}},
            status_code=200
        )

        regulation_response = {"errors": [{
            "status": "500",
            "title": "INTERNAL_SERVER_ERROR",
            "detail": "Incorrect result size: expected 1, actual 2"}]
        }

        mock_requests.get(
            'http://url.com?api_key=1234',
            json=regulation_response,
            status_code=500
        )

        mock_requests.put(
            'http://test.com/put_results',
            json={'success': 'The job was successfully completed'},
            status_code=200
        )
        client.job_operation()
        response = mock_requests.request_history[-1]
        assert '500' in response.json()


def test_client_sends_attachment_results2(mock_requests, mocker):
    api_validator = Validator()
    server_validator = ServerValidator('http://test.com')
    client = TempClient(server_validator, api_validator)
    client.api_key = 1234

    with mock_requests:
        mock_requests.get(
            'http://test.com/get_job',
            json={'job': {'1': 'http://url.com', 'job_type': 'attachments'}},
            status_code=200
        )
        mock_requests.get(
            'http://url.com?api_key=1234',
            json={'data': {'id': '1', 'attributes': {'agencyId': 'NOAA'},
                           'job_type': 'documents'}},
            status_code=200
        )
        mock_requests.put('http://test.com/put_results', text='{}')
        client.job_operation()

        mock_requests.put(f'{BASE_URL}/put_results', text='{}')
        client.job_operation
        put_request = mock_requests.request_history[1]
        json_data = json.loads(put_request.json())
        saved_data = json_data['results']['data']

        assert saved_data['attachments_text'] == ['http://url.com']
        assert saved_data['type'] == 'attachment'
        assert saved_data['id'] == 'http://url.com'
        assert saved_data['attributes']['agencyId'] is None
        assert saved_data['attributes']['docketId'] is None
        assert saved_data['attributes']['commentOnDocumentId'] is None