
class DexScreenerDataError(Exception):
    """Raised when there is an issue fetching or processing data from DexScreener API."""
    def __init__(self, message="Error fetching or processing data from DexScreener API"):
        self.message = message
        super().__init__(self.message)

class DexScreenerTokenError(Exception):
    """Raised when the provided token is invalid and equal to Solana address."""
    def __init__(self, message="Incorrect baseToken provided"):
        self.message = message
        super().__init__(self.message)