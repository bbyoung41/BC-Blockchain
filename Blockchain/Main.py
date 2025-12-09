from blockchain import BlockChain
from Wallet import Wallet
from Networking.Node import Node
from GUI.app import app
import threading
import time

def main():
    # Initialize everything
    print("Starting Blockchain System...")

    # Load or create blockchain
    blockchain = BlockChain()

    # Create or load wallets
    mywallet = Wallet()
    mywallet.read_wallet()
    print(f"Wallet : {mywallet.address} has been loaded")

    # START NODE SERVER IN BACKGROUND THREAD
    My_Node = Node(port=5000, host='10.238.72.75') # Your node class
    server_thread = threading.Thread(target=My_Node.start_server, daemon=True)
    server_thread.start()
    print(f"Node server started on port 5000 in background...")

    # OPTIONAL: Connect to network
    My_Node.setup()  # Connect to bootstrap/peers

    # Check if blockchain uptodate
    latest_hash = blockchain.get_latest_block_hash()
    My_Node.update_blockchain(latest_hash)

    latest_tx = blockchain.get_latest_tx()
    My_Node.update_tx(latest_tx)

    # Pass objects to Flask
    app.config['node'] = My_Node
    app.config['blockchain'] = blockchain
    app.config['wallet'] = mywallet

    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()