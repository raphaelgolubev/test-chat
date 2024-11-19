from asyncio import TimeoutError as ConnectionTimeoutError

class InvalidHelloError(Exception):
    ...