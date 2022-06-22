from enum import Enum


class ValidationWords(Enum):
    """Verbs specified in RKSOK specs for requests to vragi-vezde.to.digital and answers from it"""
    IS_ALLOWED = "АМОЖНА?"
    ALLOWED = "МОЖНА"
    FORBIDDEN = "НИЛЬЗЯ"


class RequestVerbs(Enum):
    """Verbs specified in RKSOK specs for requests"""
    GET = "ОТДОВАЙ"
    DELETE = "УДОЛИ"
    WRITE = "ЗОПИШИ"


class ResponseWords(Enum):
    """Verbs specified in RKSOK specs for response to client"""
    INCORRECT = "НИПОНЯЛ"
    OK = "НОРМАЛДЫКС"
    NOT_FOUND = "НИНАШОЛ"


