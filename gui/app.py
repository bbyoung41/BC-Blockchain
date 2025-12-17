from flask import Flask, render_template, jsonify, request
import json
import time
from datetime import datetime
import random

app = Flask(__name__,
    static_folder = 'static',  # Custom static folder path
)

# Custom filter for formatting timestamps
@app.template_filter('format_time')
def format_time_filter(timestamp):
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return timestamp

@app.route('/')
def dashboard():
    """Main dashboard page"""
    wallet = app.config.get('wallet')
    node = app.config.get('node')
    blockchain = app.config.get('blockchain')

    wallet_address = wallet.address if wallet else 'Unknown'

    # Get pending transactions
    pending_transactions = my_pending_transactions()
    recent_transactions = my_recent_transactions()

    return render_template('dashboard.html',
                           wallet_address=wallet_address,
                           balance=blockchain.get_balance(wallet.address) if all([blockchain, wallet]) else 0,
                            recent_transactions = reversed(recent_transactions),
                            pending_transactions_len = len(pending_transactions),
                            pending_transactions = reversed(pending_transactions),
                           block_height = blockchain.block_height
                            )

@app.route('/send')
def send_page():
    """Send funds page"""
    wallet = app.config.get('wallet')
    node = app.config.get('node')
    blockchain = app.config.get('blockchain')
    return render_template('send.html', balance=blockchain.get_balance(wallet.address) if all([blockchain, wallet]) else 0)

@app.route('/network')
def network_page():
    """Network status page"""
    node = app.config.get('node')
    return render_template('blockchain.html',
                           node_id=getattr(node, 'node_id', 'Unknown'),
                           node_port=getattr(node, 'port', 'Unknown'))


@app.route('/api/status')
def api_status():
    """JSON API for dashboard data"""
    node = app.config.get('node')
    wallet = app.config.get('wallet')
    blockchain = app.config.get('blockchain')

    balance = blockchain.get_balance(wallet.address) if all([blockchain, wallet]) else 0
    block_height = len(blockchain.chain) if blockchain else 0
    peer_count = len(node.peers) if node else 0
    pending_tx = len(node.pending_transactions) if node else 0

    return jsonify({
        'balance': balance,
        'block_height': block_height,
        'peer_count': peer_count,
        'pending_transactions': pending_tx
    })


@app.route('/send', methods=['POST'])
def send_transaction():
    node = app.config.get('node')
    wallet = app.config.get('wallet')
    blockchain = app.config.get('blockchain')

    # Check balance from local blockchain
    balance = blockchain.get_balance(wallet.address)
    recipient = request.form.get('recipient', '').strip()
    amount = float(request.form.get('amount', '').strip())

    check_balance = False
    while check_balance:
        if balance < amount:
            print(f"Insufficient funds, Current balance = {balance}")
        else:
            check_balance = False

    recipient_address = recipient
    transaction = wallet.create_transaction(recipient_address=recipient_address, amount=amount)

    # BROADCAST TRANSACTION TO NETWORK
    validation_id = node.broadcast_transaction(transaction=transaction.to_dict())

    print("Transaction broadcasted to network!")
    time.sleep(10)
    validation_status = 'Pending'
    while validation_status == 'Pending':
        validation_status = node.check_validation_status(validation_id)

    if validation_status == 'Valid':
        blockchain.add_transactions(transaction)
        # Send to others in the network the validated transaction
        node.broadcast_transaction(transaction=transaction.to_dict(), status='Validated')

        # Add transaction to be displayed in the frontend
        print("Transaction added to pool!")

        #Check if time for mining
        mined = False
        with open('my_data/pending_transactions.json') as f:
            pending_tx = json.load(f)
        if len(pending_tx) >= 5:
            print("Mining a new block")
            # Mine
            new_block = blockchain.mine_block(address=wallet.address)

            if new_block:
                print(" New block mined!")
                node.broadcast_new_block(new_block)
                print("New block broadcasted to network!")
                mined = True


        # Send back to the frontend that the transaction has been validated
        # Return success page with empty form
        return render_template('tx_complete.html',
                               amount=amount,
                               recipient=recipient,
                               tx_id= validation_id,
                               form_data=None,  # Clear form
                               error=None,
                               mined = mined,
                               success=True)

    elif validation_status == 'Invalid':
        #Send back to the front end telling them the transaction was invalid
        return render_template('tx_complete.html',
                               amount=amount,
                               recipient=recipient,
                               tx_id=validation_id,
                               form_data=None,  # Clear form
                               error=None,
                               success=False)


@app.route('/api/peers')
def api_peers():
    """Get peer list"""
    node = app.config.get('node')
    peers = []

    if node:
        for host, port in node.peers:
            peers.append({
                'host': host,
                'port': port,
                'status': 'Connected'
            })

    return jsonify(peers)

def my_recent_transactions(limit=5):
        recent_tx = []

        with open('my_data/blockchain.json', 'r') as f:
            blockchain = json.load(f)

        with open('my_data/Wallets/wallet.json') as f:
            wallet = json.load(f)

        # Go through blocks in reverse order (newest first)
        for block in reversed(blockchain[-5:]):
            for tx in block['transactions']:
                if 'sender' in tx:
                    if tx['sender'] == wallet:
                        recent_tx.append(tx)
                if tx['recipient'] == wallet:
                    recent_tx.append(tx)
                    if len(recent_tx) >= limit:
                        return recent_tx

        print(recent_tx)
        return recent_tx

def my_pending_transactions():
    try:
        with open('my_data/pending_transactions.json', 'r') as f:
            tx_data = json.load(f)
            return [tx_dict for tx_dict in tx_data]
    except FileNotFoundError:
        return []


def generate_mock_blockchain_data():
    """Generates blockchain data in the format expected by the D3 frontend."""
    path = 'my_data/blockchain.json'
    with open(path, 'r') as f:
        blockchain = json.load(f)
    num_blocks = len(blockchain)
    nodes = []
    links = []
    no_block = -1

    for block in blockchain:
        no_block += 1
        # Generate a unique hash for the block
        block_hash = block['hash']

        nodes.append({
            "id": f"block-{no_block}",
            "type": "block",
            "height": no_block,
            "hash": block_hash,
            "expanded": False,
            # In a real app, you'd fetch the actual transaction count
            "tx_count": len(block['transactions'])
        })

        if no_block > 0:
            # Link the current block to the previous one
            links.append({
                "source": f"block-{no_block - 1}",
                "target": f"block-{no_block}",
                "type": "chain"
            })

    return {"nodes": nodes, "links": links}


@app.route('/api/blockchain', methods=['GET'])
def get_blockchain_data():
    """Endpoint to serve the blockchain data."""
    data = generate_mock_blockchain_data()
    return jsonify(data)


def generate_mock_transaction_details(block_id, count):
    """Generates a list of detailed transaction objects."""
    path = 'my_data/blockchain.json'
    with open(path, 'r') as f:
        blockchain = json.load(f)
    block = blockchain[int(block_id[-1])]
    transactions = []

    for tx in block['transactions']:
        # Generate mock addresses and values
        if 'sender' in tx:
            sender = tx['sender']
        else:
            sender = 'reward'
        recipient = tx['recipient']
        tx_hash = tx['tx_hash']
        value = tx['amount']

        transactions.append({
            "hash": tx_hash,
            "sender": sender,
            "recipient": recipient,
            "value": value
        })

    return transactions


# NEW ROUTE: Accepts the block ID from the URL path
@app.route('/api/transactions/<block_id>', methods=['GET'])
def get_transaction_details(block_id):
    """
    Endpoint to fetch transaction details for a specific block.

    The frontend passes the expected count as a query parameter.
    """
    try:
        # Get the 'count' query parameter from the URL (e.g., ?count=5)
        count = int(request.args.get('count', 1))
    except ValueError:
        count = 1

    details = generate_mock_transaction_details(block_id, count)
    return jsonify(details)

if __name__ == '__main__':
    app.run(debug=True)