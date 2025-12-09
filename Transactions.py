import hashlib
import ecdsa
import json


class Transactions:
    def __init__(self, sender, recipient, amount, sender_public_key, index=0):
        self.amount = amount
        self.recipient = recipient
        self.sender  = sender
        self.signature = None
        self.tx_hash = self.calculate_hash()
        self.sender_public_key = sender_public_key
        self.index = index

    def calculate_hash(self):
        data_string = f"{self.amount}{self.recipient}{self.sender}{self.signature}"
        return hashlib.sha256(data_string.encode()).hexdigest()

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'index': self.index,
            'tx_hash': self.tx_hash,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'signature': self.signature,
            'sender_public_key':self.sender_public_key,
        }

    def is_valid(self, wallet_address = None, validation_type = 'Easy'):
        """Validate transaction structure and signature"""
        # Check basic structure

        if not all([self.sender, self.recipient, self.amount > 0, self.signature]):
            return False

        # Verify signature
        return self.verify_signature()


    def verify_signature(self):
        """Verify the transaction signature"""
        if not self.signature:
            return False

        # Recreate the signed data
        signable_data = f"{self.sender}{self.recipient}{self.amount}"

        try:
            # Verify using sender's public key
            public_key_bytes = bytes.fromhex(self.sender_public_key)
            verifying_key = ecdsa.VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)

            return verifying_key.verify(bytes.fromhex(self.signature), signable_data.encode())

        except:
            return False

    @classmethod
    def from_dict(cls, data):
        transaction = cls(
            index = data['index'],
            sender=data['sender'],
            recipient=data['recipient'],
            amount=data['amount'],
            sender_public_key = data['sender_public_key']
        )
        transaction.tx_hash = data['tx_hash']
        transaction.signature = data['signature']
        return transaction


