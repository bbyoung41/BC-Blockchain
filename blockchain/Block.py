import hashlib
import json


class Block:
    def __init__(self, transactions, index, prev_hash, version):
        self.index = index
        self.version = version
        self.transactions = transactions
        self.prev_hash = prev_hash
        self.nonce = 0
        self.difficulty = 2
        self.current_hash = self.calculate_block_hash()
        self.merkel_root = self.cal_merkel_root()


    def cal_merkel_root(self):
        transaction_list = [tx.tx_hash for tx in self.transactions]

        current_level = []
        for value in transaction_list:
            if isinstance(value, str):
                hashed = hashlib.sha256(value.encode()).hexdigest()
            else:
                hashed = hashlib.sha256(value.to_bytes(8, 'big')).hexdigest()
            current_level.append(hashed)


        while len(current_level) > 1:
            next_level = []  # Reset for each iteration

            for i in range(0, len(current_level), 2):
                # Get left element
                left = current_level[i]

                # Check if right element exists
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left  # Duplicate if odd number

                # Combine and hash (or in your case, add numbers)
                combined = left + right
                combined_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(combined_hash)

            current_level = next_level
              # Debug output

        return current_level[0]

    def calculate_block_hash(self):
        header_data = {
            'version':1,
            'previous_hash': self.prev_hash,
            'nonce': self.nonce,
            'merkel_root': self.cal_merkel_root()
        }
        header_string = json.dumps(header_data, sort_keys=True)
        return hashlib.sha256(header_string.encode()).hexdigest()

    def mining(self):
        while self.calculate_block_hash()[:self.difficulty] != "0" * self.difficulty:
            self.nonce += 1
            self.current_hash = self.calculate_block_hash()
        data = [self.current_hash, self.nonce]
        return data


    def block_header(self):
        mining_data  = self.mining()
        block_header = {
            "version": self.version,  # Protocol version
            "index": self.index,  # Block height/number
            "previous_hash": self.prev_hash,
            "merkle_root": self.merkel_root,
            "nonce": mining_data[1],
            "difficulty": 4,
            "hash": mining_data[0],
        }
        return block_header



