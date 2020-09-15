import requests
import json

DEFAULT_TIMEOUT=60

class RestServer(object):
    def __init__(self, server, port, token=None, use_ssl=None):
        self.server = server
        self.port = port
        self.use_ssl = use_ssl
        self._headers = {'X-AUTH-TOKEN': token, 
                         'Content-type': 'application/json; charset="UTF-8"'}

    def _get_url(self, path):
        return "%s://%s:%s/%s" % ('https' if self.use_ssl else 'http',
                                  self.server, self.port, path)

    def get(self, path, timeout=DEFAULT_TIMEOUT):
        resp = requests.get(self._get_url(path), headers=self._headers,
            verify=False, timeout=timeout)
        if resp.status_code == 200:
            return json.loads(resp.text)
        else:
            raise Exception("%s: %s"%(resp.status_code, resp.text))

    def post(self, path, payload_dict, timeout=DEFAULT_TIMEOUT):
        payload = json.dumps(payload_dict)
        resp = requests.post(self._get_url(path), data=payload,
            headers=self._headers, verify=False, timeout=timeout)
        if resp.status_code == 200:
            return json.loads(resp.text)
        else:
            raise Exception("%s: %s"%(resp.status_code, resp.text))

    def put(self, path, payload_dict, timeout=DEFAULT_TIMEOUT):
        payload = json.dumps(payload_dict)
        resp = requests.put(self._get_url(path), data=payload,
            headers=self._headers, verify=False, timeout=timeout)
        if resp.status_code == 200:
            return json.loads(resp.text)
        else:
            raise Exception("%s: %s"%(resp.status_code, resp.text))

    def delete(self, path, timeout=DEFAULT_TIMEOUT):
        resp = requests.delete(self._get_url(path), headers=self._headers,
            verify=False, timeout=timeout)
        if resp.status_code == 200:
            return json.loads(resp.text)
        else:
            raise Exception("%s: %s"%(resp.status_code, resp.text))
