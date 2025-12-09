from coin_base_transactions import CoinBase
from Transactions import Transactions
from Block import Block
import json

class BlockChain:

    def __init__(self):
        self.founder_address = "1HZN9b2CbZHQS9FULHWmeeLKcGkgf6Pxe6"
        self.chain = []
        self.transaction_to_add = []
        self.max_transaction_per_block = 5
        self.pending_transactions = self.load_pending_transactions()
        self.block_height = self.find_block_height()


    def create_genesis_block(self):
        # Creating first transaction
        transaction = CoinBase(recipient=self.founder_address, amount=10000)

        genesis_block = Block(transactions= [transaction], index=0, prev_hash="0" * 64, version = 1)
        block_data = genesis_block.block_header()
        block_data["transactions"] = transaction.to_dict()
        self.chain.append(block_data)
        with open("../My_Data/blockchain.json", "w") as f:
            json.dump(self.chain, f)

    def load_pending_transactions(self):
        try:
            with open('../My_Data/pending_transactions.json', 'r') as f:
                tx_data = json.load(f)
                return [Transactions.from_dict(tx_dict) for tx_dict in tx_data]
        except FileNotFoundError:
            return []  # No pending transactions file yet

    def add_transactions(self, transaction):
        if transaction.is_valid():
            self.transaction_to_add.append(transaction)
            self.save_pending_transactions()  # Save after each addition!
            print(f"Transaction added to pending pool ({len(self.transaction_to_add)} total)")
            return True
        return False

    def save_pending_transactions(self):
        transactions_to_save = self.transaction_to_add[0].to_dict()

        with open('../My_Data/pending_transactions.json', 'r') as f:
            all_pending_tx = json.load(f)
        transactions_to_save['index'] = len(all_pending_tx)
        all_pending_tx.append(transactions_to_save)

        with open('../My_Data/pending_transactions.json', 'w') as f:
            json.dump(all_pending_tx, f, indent=2)

    def prev_hash(self):
        with open("../My_Data/blockchain.json", "r") as f:
            blocks = json.load(f)
        return blocks[-1]['hash']

    def mine_block(self, address):
        block_transactions = []
        # Retrieve data from the pending_transactions.json
        transactions = self.load_pending_transactions()


        # Add the reward_tx to transactions folder
        reward_tx = CoinBase(recipient=address, amount=10)
        transactions.append(reward_tx)

        # Calculate block index
        with open("../My_Data/blockchain.json", "r") as f:
            blocks = json.load(f)
        index = (blocks[-1]['index']) + 1

        # Call the block class to create a new_block
        block_object = Block(transactions=transactions, index=index, prev_hash=self.prev_hash(), version=1)
        block_data = block_object.block_header()
        # Turn it back to list format
        for tx in transactions:
            block_transactions.append(tx.to_dict())

        block_data["transactions"] = block_transactions

        self.save_new_block(block = block_data, path ="../My_Data/blockchain.json", path_pending_tranx='../My_Data/pending_transactions.json')

        # Return back the block to be sent to the rest of the network
        return block_data

    #ALERT: Path parameter was for test purposes, you may remove it during production
    @staticmethod
    def save_new_block(block, path, path_pending_tranx):
        #Save to blockchain
        with open(path, "r") as f:
            existing_transactions = json.load(f)

        # Check if block contains prev_block_hash
        latest_block = existing_transactions[-1]
        latest_block_hash = latest_block['hash']
        current_block_prev_hash = block["previous_hash"]

        if current_block_prev_hash == latest_block_hash:
            existing_transactions.append(block)

            with open(path, "w") as f:
                json.dump(existing_transactions, f)

            # Delete existing pending_transactions
            with open(path_pending_tranx, 'w') as f:
                json.dump([], f)

        else:
            print("The broadcasted block has an Invalid block hash sequence to that of the blockchain")

    @staticmethod
    def get_balance(address):
        balance = 0

        # Read the blockchain file
        with open('../My_Data/blockchain.json', 'r') as f:
            blockchain = json.load(f)

        # Calculating Balance
        for block in blockchain:
            # Check every transaction in each block
            for transaction in block['transactions']:
                # If this address received money, add to balance
                if transaction['recipient'] == address:
                    balance += transaction['amount']

                # If this address sent money, subtract from balance
                if 'sender' in transaction:
                    if transaction['sender'] == address:
                        balance -= transaction['amount']

        #Also check validated pending transactions
        with open('../My_Data/pending_transactions.json', 'r') as f:
            pending_transactions = json.load(f)

        #Calculating Balance
        for tranx in pending_transactions:
            # If this address received money, add to balance
            if tranx['recipient'] == address:
                balance += tranx['amount']

            # If this address sent money, subtract from balance
            if tranx['sender']:
                if tranx['sender'] == address:
                    balance -= tranx['amount']

        return balance

    def get_latest_block_hash(self):
        path = '../My_Data/blockchain.json'
        with open(path, 'r') as f:
            blockchain = json.load(f)

        #Get latest hash
        latest_block = blockchain[-1]
        latest_block_hash = latest_block['hash']

        return latest_block_hash

    def get_latest_tx(self):
        with open('../My_Data/pending_transactions.json') as f:
            pending_tx = json.load(f)
        if len(pending_tx) == 0:
            print("Empty")
            return 'Empty'
        else:
            print(pending_tx[-1]["tx_hash"])
            return pending_tx[-1]["tx_hash"]

    def find_block_height(self):
        with open('../My_Data/blockchain.json', 'r') as f:
            blockchain = json.load(f)

        return len(blockchain)






