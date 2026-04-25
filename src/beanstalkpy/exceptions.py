class BeanstalkError(Exception):
    """Base exception for all beanstalkpy errors."""
    pass

class ConnectionError(BeanstalkError):
    """Raised when there is a connection issue."""
    pass

class ProtocolError(BeanstalkError):
    """Raised when the server sends an unexpected response."""
    pass

class CommandError(BeanstalkError):
    """Base class for errors returned by the beanstalkd server."""
    pass

class OutOfMemoryError(CommandError):
    """The server cannot allocate enough memory for the job."""
    pass

class InternalError(CommandError):
    """This indicates a bug in the server."""
    pass

class BadFormatError(CommandError):
    """The client sent a command line that was not well-formed."""
    pass

class UnknownCommandError(CommandError):
    """The client sent a command that the server does not know."""
    pass

class ExpectedCRLFError(CommandError):
    """The job body must be followed by a CR-LF pair."""
    pass

class JobTooBigError(CommandError):
    """The client has requested to put a job with a body larger than max-job-size bytes."""
    pass

class DrainingError(CommandError):
    """The server is in drain mode and is no longer accepting new jobs."""
    pass

class NotFoundError(CommandError):
    """The requested job or tube does not exist, or the job is not in a state that allows the operation."""
    pass

class NotIgnoredError(CommandError):
    """The client attempts to ignore the only tube in its watch list."""
    pass

class TimedOutError(CommandError):
    """The reserve command timed out."""
    pass

class DeadlineSoonError(CommandError):
    """The safety margin arrived while the client was waiting on a reserve command."""
    pass
