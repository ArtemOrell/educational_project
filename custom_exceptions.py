class NotSpecifiedIPOrPortError(Exception):
    """Error that occurs when there is not Server or Port
    specified in command-line arguments."""
    pass


class CanNotParseRequestError(Exception):
    """Error that occurs when we can not parse some strange
        request to RKSOK server."""
    pass


class CanNotParseResponseError(Exception):
    """Error that occurs when we can not parse some strange
        response from vragi-vezde.to.digital server."""
    pass


class CannotFetchDataFromValidationServer(Exception):
    """Errors that occurs when we cannot fetch any data from validation server """
    pass
