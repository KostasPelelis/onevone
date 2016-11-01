import requests
import time
import io
import hashlib


class ForbiddenException(Exception):
    def __init__(self, message):
        super(ForbiddenException, self).__init__(message)


class NotFound(Exception):
    def __init__(self, message):
        super(NotFound, self).__init__(message)


class RESTClient(object):

    base_url = ''
    timeout = 10

    def __init__(self, base_url='', timeout=10, log=None):
        self.base_url = base_url
        self.timeout = timeout
        self.log = log
        self.headers = {}

    def get(self, url=None, endpoint=None,
            payload=None, response_type='json'):
        if url is None:
            _url = '{0}{1}'.format(self.base_url, endpoint)
        elif isinstance(url, str):
            _url = '{0}{1}'.format(url, endpoint)
        else:
            raise Exception('Unknown url')
        url_hash = hashlib.md5(_url.encode('utf-8')).hexdigest()[:6]
        self.log.debug('[GET {0}] {1}, params={2}'.format(
            url_hash, _url, payload))
        try:
            response = requests.get(_url, params=payload, headers=self.headers)
            if self.timeout > 0:
                while not self.handle_response(response, url_hash):
                    response = requests.get(_url, params=payload,
                                            headers=self.headers)
        except ForbiddenException as e:
            raise e
        except NotFound as e:
            raise e
        except Exception as e:
            raise e
        # TODO: Check Content-Type Header
        if response_type == 'json':
            return response.json()
        elif response_type == 'byte-stream':
            return io.BytesIO(response.content)
        elif response_type == 'any':
            return response.content

    def set_header(header_name=None, header_val=None):
        if header_name and header_val:
            self.headers[header_name] = header_val

    def handle_response(self, response, hash):
        if response.status_code != 200:
            if response.status_code == 403:
                raise ForbiddenException('Forbidden Endpoint')
            elif response.status_code == 404:
                self.log.error(
                    '[{0} status=404] Resource not Found! '
                    'exiting...'
                    .format(hash))
                raise NotFound('Forbidden Endpoint')
            elif response.status_code == 429:
                rate_limit_header = response.headers.get('X-Rate-Limit-Type')
                # If we actaully exceeded the requests that we were supposed
                # to do in a given amount of time
                if rate_limit_header is not None:
                    retry_after = response.headers.get('Retry-After', 10)
                    self.log.error('[{0} status=429] Rate Limit Exceeded! Type: {1}. '
                                   'Retrying after {2} seconds...'.format(
                                    hash, rate_limit_header, retry_after))
                    time.sleep(int(retry_after))
                else:
                    self.log.error(
                        '[{0} status=429] Rate Limit Exceeded because of the '
                        'underlying service! Retrying after {1} seconds...'
                        .format(hash, self.timeout))
                    time.sleep(self.timeout)
            elif response.status_code >= 500:
                self.log.error(
                    '[{0} status={1}] Service unavailable! Sleeping for {2} '
                    'seconds'.format(hash, response.status_code, self.timeout))
                time.sleep(self.timeout)
            else:
                self.log.error(
                    '[{0} status={1}] Unknown Error! '
                    'sleeping just in case...'
                    .format(hash, response.status_code))
                time.sleep(self.timeout)

            return False

        self.log.info('[{0} status=200] Ok!'.format(hash))
        return True
