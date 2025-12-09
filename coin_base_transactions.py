import hashlib

class CoinBase:
    """Special transaction for creating new coins"""

    def __init__(self, recipient, amount, block_height=None):
        self.sender = None  # No sender - coins are created
        self.recipient = recipient
        self.amount = amount
        self.block_height = block_height
        self.signature = "coinbase"
        self.tx_hash = self.calculate_hash()
        self.version = 2

    def calculate_hash(self):
        data = f"coinbase{self.recipient}{self.amount}{self.block_height}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return {
            'recipient': self.recipient,
            'amount': self.amount,
            'block_height': self.block_height,
            'tx_hash': self.tx_hash,
            'version':self.version,
        }

    def is_valid(self):
        return (self.recipient is not None and
                self.amount > 0 and
                self.sender is None)