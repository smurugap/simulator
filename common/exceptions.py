from flask import jsonify
class InvalidUsage(Exception):
    status_code = 400
    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class ProtocolError(Exception):
    """Raise when SNMP protocol error occured"""

class ConfigError(Exception):
    """Raise when config error occured"""

class BadValueError(Exception):
    """Raise when bad value error occured"""

class WrongValueError(Exception):
    """Raise when wrong value (e.g. value not in available range) error occured"""

