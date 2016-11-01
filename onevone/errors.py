class MatchupNotFound(Exception):

    def __init__(self, message):
        super(MatchupNotFound, self).__init__(message)


class BadRequest(Exception):

    def __init__(self, message):
        super(BadRequest, self).__init__(message)
