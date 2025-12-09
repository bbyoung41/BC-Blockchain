import hashlib
import base58
import os
import json
import ecdsa

from ecdsa import SigningKey, SECP256k1

from Transactions import Transactions


class Wallet:
    def __init__(self):
        self.public_key_hex = None
        self.private_key_hex = None
        self.private_key = None
        self.public_key = None
        self.address = None
        self.balance = None
        self.wallet_available()


    def wallet_available(self):
        file_path = "../My_Data/Wallets/wallet.json"
        if os.path.exists(file_path):
            print(f"The file '{file_path}' exists.")
        else:
            print(f"The file '{file_path}' does not exist.")
            create_new = True
            if create_new:
                self.create_new_wallet()

    def create_new_wallet(self):

        # Generate keys
        self.generate_keys()

        print("🎉 New Wallet Created!")
        print(f"Address:    {self.address}")
        print(f"Public Key: {self.public_key_hex[:64]}...")
        print(f"Private Key: {self.private_key_hex[:64]}... [KEEP SECRET!]")

        self.save_wallet()

        return self.address

    def generate_keys(self):
        #Generate private_key
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.private_key_hex = self.private_key.to_string().hex()

        #Generate public key
        self.public_key = self.private_key.verifying_key
        self.public_key_hex = self.public_key.to_string().hex()

        #Address
        self.address = self.generate_address()

    def generate_address(self):
        """Generate wallet address from public key - CORRECTED"""
        # Step 1: Hash the public key with SHA-256
        public_key_bytes = bytes.fromhex(self.public_key_hex)
        sha256_hash = hashlib.sha256(public_key_bytes).digest()

        # Step 2: Make it shorter
        ripemd160 = hashlib.new('ripemd160', sha256_hash)
        public_key_hash = ripemd160.digest()

        # Step 3: Add version byte
        version_byte = b'\x00'  # Bitcoin mainnet
        versioned_payload = version_byte + public_key_hash

        # Step 4: Calculate checksum
        checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]

        # Step 5: Combine and encode in Base58
        binary_address = versioned_payload + checksum
        address_bytes = base58.b58encode(binary_address)  # Returns bytes
        address = address_bytes.decode('utf-8')  # Convert to string

        return address

    def save_wallet(self):
        wallet_data = {
            'Address': self.address,
            'Public Key':self.public_key_hex,
            'Private Key':self.private_key_hex
        }

        with open('../My_Data/Wallets/wallet.json', 'w') as f:
            json.dump(wallet_data, f)

    def read_wallet(self):
        with open('../My_Data/Wallets/wallet.json', 'r') as f:
            wallet_data = json.load(f)
        self.private_key_hex = wallet_data['Private Key']
        self.public_key_hex = wallet_data['Public Key']
        self.address = wallet_data['Address']

    def create_transaction(self, recipient_address, amount):

        self.read_wallet()

        transaction = Transactions(
            sender=self.address,
            recipient= recipient_address,
            amount=amount,
            sender_public_key = self.public_key_hex
        )

        self.sign_transaction(transaction)

        return transaction

    def sign_transaction(self, transaction):
        signable_data = f"{transaction.sender}{transaction.recipient}{transaction.amount}"

        #sign with private key
        signature = self._sign_data(signable_data)

        transaction.signature = signature

    def _sign_data(self, data):
        """Sign data using the wallet's private key"""
        # Convert private key from hex to signing key object
        private_key_bytes = bytes.fromhex(self.private_key_hex)
        signing_key = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)

        # Sign the data
        signature = signing_key.sign(data.encode())
        return signature.hex()
