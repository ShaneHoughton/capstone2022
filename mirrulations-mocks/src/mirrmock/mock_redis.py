import redis

class BusyRedis():
    """
    Stub for testing in place of a Redis server that is busy loading the data to memory, 
    ping replies with true
    """
    def ping(self):
        raise redis.BusyLoadingError

class ReadyRedis():
    """
    Stub for testing in place of an active Redis server, 
    ping replies with true
    """
    def ping(self):
        return True