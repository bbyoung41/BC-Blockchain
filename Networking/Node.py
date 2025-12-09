import socket
import threading
import json
import os
import time
import struct
from struct import pack_into
from time import process_time_ns
from wsgiref.validate import validator

from Transactions import Transactions
from Blockchain.blockchain import BlockChain

class Node:
    def __init__(self, port, host='localhost'):
        self.host = host
        self.port = port
        self.peers = self.load_peers_from_file()
        self.running = True
        self.current_active_peers = []
        self.blockchain_path = '../My_Data/blockchain.json'

        self.node_id = f"node_{host}_{port}"  # Unique identifier
        self.capabilities = ['transaction_relay', 'block_validation']

        self.active_outgoing_connections = {}
        self.DEFAULT_BOOTSTRAP_NODES = [  # Primary bootstrap
            ('10.238.72.75', 5000),  # Secondary bootstrap
        ]

        self.pending_validation_ids = []
        self.pending_validation = {}

    def setup(self):
        if self.port == 5000:
            pass
        elif os.path.exists(self.blockchain_path):
            pass
        else:
            self.connect_to_bootstrap()

    def connect_to_bootstrap(self):
        data = {"type": "BLOCKCHAIN_DATA", "content": "Hello!"}
        for host, port in self.DEFAULT_BOOTSTRAP_NODES:
            try:
                print("Connecting to bootstrap node")

                # Connecting to bootstrap
                if (host, port) not in self.active_outgoing_connections:
                    self.connect_to_peer_with_handshake(host=host, port=port, connection_type="BOOTSTRAP")

            except Exception as e:
                print(f"Error at connection_to_bootstrap method : {e}")

    def process_received_blockchain(self, blockchain):
        try:
            # message['content'] is a JSON string that needs parsing
            blockchain_json_string = blockchain

            # Convert JSON string back to Python objects
            blockchain_data = blockchain
            print(blockchain_data)

            # Now save as proper .json file
            folder_path = '../My_Data/blockchain.json'
            file_name = 'blockchain.json'
            file_path = os.path.join(folder_path, file_name)

            try:
                with open(folder_path, "w") as f:  # "w" mode creates a new file or overwrites if it exists
                    json.dump(blockchain_data, f, indent=2)
                print(f"File '{file_name}' created in '{folder_path}'.")
            except IOError as e:
                print(f"Error creating file: {e}")

            print(f"Saved {len(blockchain_data)} {file_path}")

        except Exception as e:
            print(f"Error processing blockchain data: {e}")

    def connect_to_peer_with_handshake(self, host, port, connection_type="REGULAR"):
        try:
            print(f" Connecting to {host}:{port} as {connection_type} peer...")

            if (host, port) not in self.active_outgoing_connections:
                # Create connection using existing method
                socket_obj = socket.socket()
                socket_obj.connect((host, port))
                self.active_outgoing_connections[(host, port)] = socket_obj

                # Start listener using existing method
                threading.Thread(
                    target=self._listen_to_peer,
                    args=(socket_obj, (host, port)),
                    daemon=True
                ).start()
                print(f"Established connection to {host}:{port}")

            # SEND APPROPRIATE HANDSHAKE BASED ON CONNECTION TYPE
            if connection_type == "BOOTSTRAP":
                handshake_msg = self._create_bootstrap_handshake()
            elif connection_type == "REGULAR":
                handshake_msg = self._create_peer_handshake()
            else:
                handshake_msg = self._create_basic_handshake()

            # Send handshake using existing method
            self._send_to_peer(host, port, handshake_msg)
            print(f" Sent {connection_type} handshake to {host}:{port}")
            print(f" Sent {connection_type} handshake to {host}:{port}")

            return True

        except Exception as e:
            print(f"Failed to connect to {host}:{port}: {e}")
            return False

    def _create_bootstrap_handshake(self):
        return {
            'type': 'JOIN_NETWORK_REQUEST',
            'node_address': (self.host, self.port),
            'node_id': self.node_id,
            'capabilities': self.capabilities,
            'blockchain_height': 0,
            'timestamp': time.time(),
            'handshake_type': 'BOOTSTRAP'
        }

    def _create_peer_handshake(self):
        """Create handshake for regular peers"""
        return {
            'type': 'PEER_HANDSHAKE',
            'node_address': (self.host, self.port),
            'node_id': self.node_id,
            'capabilities': self.capabilities,
            'timestamp': time.time(),
            'handshake_type': 'REGULAR'
        }

    def _create_basic_handshake(self):
        """Basic handshake for unknown peer types"""
        return {
            'type': 'BASIC_HANDSHAKE',
            'node_address': (self.host, self.port),
            'node_id': self.node_id,
            'timestamp': time.time()
        }

    def handle_handshake_request(self, message, client_address, connection_socket):
        """Handle incoming handshake requests (bootstrap node side)"""
        try:
            if message['type'] == 'JOIN_NETWORK_REQUEST':
                print(f"Handshake request from {message['node_id']}")

                # Extract their REAL listening port (not ephemeral)
                their_host, their_port = message['node_address']
                their_node_id = message['node_id']

                # Validate and accept
                if self._validate_join_request(message):
                    # Add to peers with their REAL port
                    real_peer_address = (their_host, their_port)
                    if real_peer_address not in self.peers:
                        self.peers.append(real_peer_address)
                        self.save_peers_to_file()

                    # Send welcome response
                    response = {
                        'type': 'JOIN_NETWORK_RESPONSE',
                        'status': 'accepted',
                        'message': 'Welcome to the network!',
                        'network_peers': self.peers,  # Share our peer list
                        'timestamp': time.time()
                    }

                    connection_socket.send(json.dumps(response).encode())
                    print(f"Accepted {their_node_id} on port {their_port}")

                    # Also send blockchain data
                    self._send_blockchain_to_new_node(their_host, their_port)

                else:
                    # Reject
                    response = {
                        'type': 'JOIN_NETWORK_RESPONSE',
                        'status': 'rejected',
                        'message': 'Join request invalid',
                        'timestamp': time.time()
                    }
                    connection_socket.send(json.dumps(response).encode())

        except Exception as e:
            print(f"Handshake handling error: {e}")

    def handle_handshake_response(self, message, client_address):
        """Handle handshake response (new node side)"""
        if message['type'] == 'JOIN_NETWORK_RESPONSE':
            if message['status'] == 'accepted':
                print(f"Handshake accepted! {message['message']}")

                # Connect to discovered peers
                for peer_host, peer_port in message.get('network_peers', []):
                    if (peer_host, peer_port) != (self.host, self.port):
                        print(f"Connecting to discovered peer {peer_host}:{peer_port}")
                        self._send_to_peer(peer_host, peer_port, {
                            'type': 'PEER_HANDSHAKE',
                            'node_id': self.node_id,
                            'listening_port': self.port
                        })
            else:
                print(f"Handshake rejected: {message['message']}")

    def _send_blockchain_to_new_node(self, host, port):
        # Send blockchain to newly joined node
        try:
            path = "../My_Data/blockchain.json"
            if os.path.exists(path):
                with open(path, 'r') as f:
                    blockchain_data = json.load(f)



                blockchain_msg = {
                    'type': 'BLOCKCHAIN_DATA',
                    'content': blockchain_data,
                    'timestamp': time.time()
                }

                self._send_to_peer(host, port, blockchain_msg)
                print(f"Sent blockchain to {host}:{port}")

        except Exception as e:
            print(f"Error sending blockchain: {e}")

    def start_server(self):
        """Main server loop - listens for incoming node connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)

            print(f"Node server started on {self.host}:{self.port}")

            while self.running:
                try:
                    # Wait for new connection (this blocks until connection arrives)
                    connection_socket, client_address = self.server_socket.accept()

                    print(f"Incoming connection from {client_address}")

                    # Handle this connection in a separate thread
                    self._spawn_connection_handler(connection_socket, client_address)

                except socket.timeout:
                    continue  # Timeout is normal, just keep listening
                except Exception as e:
                    if self.running:  # Only log if we're supposed to be running
                        print(f"Error accepting connection: {e}")

        except Exception as e:
            print(f"Server fatal error: {e}")
        finally:
            self._cleanup_server()

    def _spawn_connection_handler(self, connection_socket, client_address):
        """Create a new thread to handle node communication"""
        # Add to peers before starting thread to avoid race conditions

        # Create and start thread
        thread = threading.Thread(
            target=self.handle_node_communication,
            args=(connection_socket, client_address),
            daemon=True,
            name=f"NodeHandler-{client_address[1]}"  # Useful for debugging
        )
        thread.start()

        print(f"Started handler for {client_address}. Active peers: {len(self.peers)}")

    def handle_node_communication(self, connection_socket, client_address):
        """Handle all communication with a specific connected node"""
        # Note: I removed the 'n' parameter assuming you will manage buffer size internally now
        try:
            # Set timeout to detect dead connections
            connection_socket.settimeout(30.0)

            while self.running:
                # --- CHANGE 1: Read the 8-byte header first ---
                raw_msglen = self._receive_all(connection_socket, 8)
                if not raw_msglen:
                    print(f"Node {client_address} disconnected or sent no header.")
                    break

                # Unpack the length from bytes to an integer (using '!' for network byte order)
                try:
                    msglen, = struct.unpack('!Q', raw_msglen)  # Comma unpacks the tuple
                except struct.error as e:
                    print(f"Error unpacking message length from {client_address}: {e}")
                    break

                # --- CHANGE 2: Read the complete message using the exact length ---
                print(f"Expecting {msglen} bytes from {client_address}")
                full_json_data_bytes = self._receive_all(connection_socket, msglen)

                if not full_json_data_bytes:
                    print(f"Error: Incomplete data received from {client_address}.")
                    break

                # --- CHANGE 3: Process the complete, guaranteed message payload ---
                # Now you pass the ENTIRE, valid JSON payload to your processing function
                self._process_received_data(full_json_data_bytes, client_address, connection_socket)

                # The rest of your loop structure remains the same for continuous listening...

        except Exception as e:
            print(f" Communication error with {client_address}: {e}")
        finally:
            # Ensure the connection is cleaned up whether there was an error or not
            self._cleanup_node_connection(connection_socket, client_address)

    def _receive_all(self, sock, n):
        """Helper function to receive n bytes or return None if EOF is hit."""
        data = b''
        while len(data) < n:
            try:
                # Try to receive remaining bytes
                # We can't use a large static buffer size here; we ask for exactly
                # what we need remaining (n - len(data))
                packet = sock.recv(n - len(data))
                if not packet:
                    # If recv returns an empty byte string, the connection is closed
                    return None
                data += packet
            except socket.timeout:
                # Handle timeouts if your main socket has one set
                continue
            except socket.error as e:
                print(f"Socket error during reception: {e}")
                return None
        return data

    def _process_received_data(self, data, client_address, connection_socket):
        """Process and route incoming messages from nodes"""
        try:
            message = json.loads(data.decode('utf-8'))
            message_type = message.get('type')


            print(f"Received {message_type} from {client_address}")

            # Route to appropriate handler
            if message_type == "JOIN_NETWORK_REQUEST":
                self.handle_handshake_request(message, client_address, connection_socket)

            elif message_type == "JOIN_NETWORK_RESPONSE":
                self.handle_handshake_response(message, client_address)

            elif message_type == "BLOCKCHAIN_DATA":
                "Sending bootstrap data"
                self.process_received_blockchain(blockchain = message['content'])

            elif message_type == "TEST_MESSAGE":
                print(f"Received message: {message['message']} ")

            elif message_type == 'NEW_TRANSACTION':
                self._handle_new_transaction(message)

            elif message_type == 'TRANSACTION_VALIDATION':
                self.response_validation(msg = message)

            elif message_type == 'NEW_BLOCK':
                self._handle_new_block(message['block'])

            elif message_type == 'CHAIN_REQUEST':
                self._handle_chain_request(message)

            elif message_type == 'TX_REQUEST':
                self._handle_tx_update_request(message)

            elif message_type == 'PEER_LIST_REQUEST':
                self._handle_peer_list_request(connection_socket, client_address)

            elif message_type == 'HEARTBEAT':
                self._handle_heartbeat(client_address, message)
            else:
                print(f"Unknown message type: {message_type} from {client_address}")

        except json.JSONDecodeError:
            print(f"Invalid JSON received from {client_address}")
        except Exception as e:
            print(f" Error processing message from {client_address}: {e}")

    def _cleanup_node_connection(self, connection_socket, client_address):
        """Clean up when a node disconnects"""
        try:
            connection_socket.close()

            # Remove from peers list
            if client_address in self.peers:
                self.peers.remove(client_address)
                print(f"Removed {client_address} from peers. Remaining: {len(self.peers)}")

            # Notify other peers about the disconnection (optional)
            self._notify_peer_disconnection(client_address)

        except Exception as e:
            print(f" Error cleaning up {client_address}: {e}")

    def _cleanup_server(self):
        """Clean shutdown of the server"""
        print("Shutting down server...")

        # Close all active connections
        for peer in self.peers.copy():
            try:
                # In real implementation, you'd have socket references to close
                pass
            except:
                pass

        # Close main server socket
        if hasattr(self, 'server_socket'):
            self.server_socket.close()

        print("Server shutdown complete")

    def stop_server(self):
        """Gracefully stop the server"""
        self.running = False
        # Force accept() to wake up and exit
        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            temp_socket.connect((self.host, self.port))
            temp_socket.close()
        except:
            pass

    def get_server_status(self):
        """Get current server status"""
        return {
            'listening_on': f"{self.host}:{self.port}",
            'active_peers': len(self.peers),
            'is_running': self.running
        }

    def _send_to_peer(self, host, port, message):
        # Add this helper method to your BlockchainNode class
        """Send message without closing connection"""
        # Store the socket for future use
        if (host, port) not in self.active_outgoing_connections:
            # Create new persistent connection
            socket_obj = socket.socket()
            socket_obj.connect((host, port))
            self.active_outgoing_connections[(host, port)] = socket_obj

            # Start thread to listen for responses
            threading.Thread(
                target=self._listen_to_peer,
                args=(socket_obj, (host, port)),
                daemon=True
            ).start()

        # Use existing connection
        socket_obj = self.active_outgoing_connections[(host, port)]
        json_data_bytes = json.dumps(message).encode()
        msglen = len(json_data_bytes)

        # 3. Pack the length into an 8-byte binary header
        # '!' is network order, 'Q' is unsigned long long (8 bytes)
        header = struct.pack('!Q', msglen)

        # 4. Concatenate the header and the payload
        full_message = header + json_data_bytes

        socket_obj.sendall(full_message)

    def _listen_to_peer(self, socket_obj, peer_address):
        """Listen for incoming messages from a specific peer"""
        while self.running:
            try:
                data = socket_obj.recv(4096)
                if data:
                    self._process_received_data(data, peer_address, socket_obj)
                else:
                    # Peer disconnected
                    self._cleanup_node_connection(peer_address)
                    break
            except:
                self._cleanup_node_connection(peer_address)
                break

    def _validate_join_request(self, message):
        """Basic validation - just check essential fields"""
        try:
            # Check minimum required fields
            if not all(field in message for field in ['node_address', 'node_id', 'timestamp']):
                print("Missing required fields in join request")
                return False

            # Check node_address format
            node_address = message['node_address']
            if not isinstance(node_address, (list, tuple)) or len(node_address) != 2:
                print("Invalid node_address format")
                return False

            # Basic timestamp check (not from far future)
            if message['timestamp'] > time.time() + 300:  # 5 minutes in future
                print("Request timestamp too far in future")
                return False

            print("Basic validation passed")
            return True

        except Exception as e:
            print(f"Validation error: {e}")
            return False

    def save_peers_to_file(self):
        try:
            # Convert peers to serializable format
            peers_data = {
                'peers': self.peers,
                'last_updated': time.time(),
                'total_peers': len(self.peers),
                'node_id': self.node_id
            }

            file_path = '../My_Data/peers.json'

            if os.path.exists(file_path):
                # Update existing file
                with open(file_path, "r") as f:
                    data = json.load(f)
                peer_list = data['peers']
                peer_list.append(self.peers[0])

                # Update peers_data, peers key
                peers_data['peers'] = peer_list[0]

            with open(file_path, 'w') as f:
                json.dump(peers_data, f, indent=2)

            print(f"Saved {len(self.peers)} peers to {file_path}")

        except Exception as e:
            print(f"Error saving peers: {e}")

    def load_peers_from_file(self):
        path = '../My_Data/peers.json'
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            peer_list = [tuple(peer) for peer in data['peers']]

            return peer_list

        else:
            return []

    def broadcast_transaction(self, transaction, status='Unvalidated'):
        """Broadcast transaction to all peers"""
        #Add new pending_validation_id

        validation_id = len(self.pending_validation_ids) + 1
        self.pending_validation_ids.append(validation_id)
        self.pending_validation[validation_id] = 0

        transaction_message = {
            'broadcaster_host': f'{self.host}',
            'broadcaster_port': f'{self.port}',
            'validation_id': validation_id,
            'type': 'NEW_TRANSACTION',
            'status': status,
            'transaction': transaction,
            'timestamp': time.time()
        }


        for peer_host, peer_port in self.peers:
            try:
                self._send_to_peer(peer_host, peer_port, transaction_message)
                print(f"Sent transaction to {peer_host}:{peer_port}")
                # Check if the peer is already in the self.active_peers
                if peer_port not in self.current_active_peers:
                    print("added a peer to current_active_peers")
                    self.current_active_peers.append(peer_port)
                else:
                    print("Peer port already in current_active_peers")
            except:
                pass

        return validation_id

    def broadcast_new_block(self, block):
        block_message = {
            'type': 'NEW_BLOCK',
            'block': block,
            'timestamp': time.time()
        }
        for peer_host, peer_port in self.peers:
            try:
                self._send_to_peer(peer_host, peer_port, block_message)
                print(f"Sent mined block to {peer_host}:{peer_port}")
            except:
                pass

    # ALERT : This needed change to direct writing to the required location in the Blockchain folder not in the networking folder during production
    def _handle_new_transaction(self, msg):
        transaction_status = msg['status']
        if transaction_status == "Unvalidated":
            try:
                # Convert the data back to Transaction object

                tranx_object = Transactions.from_dict(msg['transaction'])

                valid = False
                #  Valid the transaction
                if tranx_object.is_valid():
                    valid = True

                else:
                    valid = False

                print(f"transaction is {valid}")
                # Send back the response
                transaction_message = {
                    'type': 'TRANSACTION_VALIDATION',
                    'is_valid': f"{valid}",
                    'Validator': f"{self.port}",
                    'validation_id': msg['validation_id']
                }

                self._send_to_peer(msg['broadcaster_host'], int(msg['broadcaster_port']), transaction_message)

            except Exception as e:
                print(f'Error at handle_new_transaction :{e}')

        elif transaction_status == 'Validated':
            path = '../My_Data/pending_transactions.json'
            # Write transaction to the pending transactions.json in mydata folder
            try:
                with open(path, 'r') as f:
                    tx_data = json.load(f)

            except FileNotFoundError:
                    tx_data = []

            # Check if the transaction is already in the file
            if msg['transaction'] not in tx_data:
                tx_data.append(msg['transaction'])

                #Save the json folder
                with open(path, 'w') as f:
                    json.dump(tx_data, f, indent=2)

                print("New transaction added to transaction pool, peer")

            elif msg['transaction'] in tx_data:
                print("Transaction already in transasction pool")

    def response_validation(self, msg):
        # Check if msg in pending_validation
        validation_id = msg['validation_id']
        print(f"This transaction validation id is {validation_id}")
        if validation_id in self.pending_validation_ids:
            # Process consensus
            if msg['is_valid'] == "True":
                self.pending_validation[validation_id] += 1
                print('one validation true')
                print(self.pending_validation)
            else:
                self.pending_validation[validation_id] -= 1
        else:
            print("Unknown id")

    def check_validation_status(self, validation_id):
        print(f"validation id {self.pending_validation[validation_id]}")
        no_active_peers = len(self.current_active_peers)
        print(f"half of the current active peers {no_active_peers / 2}")
        if self.pending_validation[validation_id] >= no_active_peers/2:
            print("this transaction is valid")
            return 'Valid'
        elif self.pending_validation[validation_id] <= -(no_active_peers/2):
            print("this transaction is invalid")
            return 'Invalid'
        else:
            return 'Pending'

    def _handle_new_block(self, block):
        path = '../My_Data/blockchain.json'
        path_2 = '../My_Data/pending_transactions.json'
        BlockChain.save_new_block(block=block, path=path, path_pending_tranx=path_2)
        print("Block successfully mined")

    def update_blockchain(self, latest_hash):
        # Sending to other peers to get latest_data
        update_status = {
            'broadcaster_host': f'{self.host}',
            'broadcaster_port': f'{self.port}',
            'type' : 'CHAIN_REQUEST',
            'latest_hash' : latest_hash,
        }

        for peer_host, peer_port in self.peers:
            try:
                self._send_to_peer(peer_host, peer_port, update_status)
                print(f"Sent Chain request to {peer_host}:{peer_port}")
            except:
                pass

    def update_tx(self, latest_tx):
        # Sending to other peers to get latest_data
        update_status = {
            'broadcaster_host': f'{self.host}',
            'broadcaster_port': f'{self.port}',
            'type' : 'TX_REQUEST',
            'latest_hash' : latest_tx,
        }

        for peer_host, peer_port in self.peers:
            try:
                self._send_to_peer(peer_host, peer_port, update_status)
                print(f"Sent update_tx request to {peer_host}:{peer_port}")
            except:
                pass

    def _handle_chain_request(self, request_data):
        path = '../My_Data/blockchain.json'
        # Check against your chain hashes
        with open(path, 'r') as f:
            blockchain = json.load(f)
        for block in blockchain:
            if block['hash'] == request_data['latest_hash']:
                current_block_index = blockchain.index(block)
                number_of_blocks_missing = len(blockchain) - (current_block_index + 1)
                missing_blocks = []
                if number_of_blocks_missing > 0:
                    for i in range(current_block_index+1, len(blockchain)):
                        missing_blocks.append(blockchain[i])

                    for m_block in missing_blocks:
                        block_message = {
                            'type': 'NEW_BLOCK',
                            'block': m_block,
                            'timestamp': time.time()
                        }
                        # send back missing blocks
                        self._send_to_peer(request_data['broadcaster_host'], int(request_data['broadcaster_port']), block_message)
                        print(f"Sent {number_of_blocks_missing} missing blocks to {request_data['broadcaster_host']}:{request_data['broadcaster_port']}")
                else:
                    block_message = {
                        'type': "TEST_MESSAGE",
                        'message': 'No missing blocks',
                        'timestamp': time.time()
                    }
                    self._send_to_peer(request_data['broadcaster_host'], int(request_data['broadcaster_port']),
                                       block_message)

        else:
                block_message = {
                    'type': "TEST_MESSAGE",
                    'message':'Unknown block hash',
                    'timestamp': time.time()
                }
                self._send_to_peer(request_data['broadcaster_host'], int(request_data['broadcaster_port']), block_message)

        #Missing transactions

    def _handle_tx_update_request(self, request_data):
        path = '../My_Data/pending_transactions.json'
        # Check against your tx hashes
        with open(path, 'r') as f:
            transactions = json.load(f)
        if request_data['latest_hash'] == 'Empty':
            #Send all transactions
            for tx in transactions:
                print(tx)
                tx_message = {
                    'type': 'NEW_TRANSACTION',
                    'transaction': tx,
                    'status': 'Validated',
                    'timestamp': time.time()
                }
                # send back missing transactions
                self._send_to_peer(request_data['broadcaster_host'], int(request_data['broadcaster_port']),
                                   tx_message)
                print(
                    f"Sent {len(transactions)} missing transactions to {request_data['broadcaster_host']}:{request_data['broadcaster_port']}")

        else:
                for tx in transactions:
                    print(tx)
                    if tx['tx_hash'] == request_data['latest_hash']:
                        current_tx_index = transactions.index(tx)
                        number_of_transactions = len(transactions) - (current_tx_index + 1)
                        missing_tx = []
                        if number_of_transactions > 0:
                            for i in range(current_tx_index + 1, len(transactions)):
                                missing_tx.append(transactions[i])

                            for m_tx in missing_tx:
                                tx_message = {
                                    'type': 'NEW_TRANSACTION',
                                    'transaction': m_tx,
                                    'status':'Validated',
                                    'timestamp': time.time()
                                }
                                # send back missing transactions
                                self._send_to_peer(request_data['broadcaster_host'], int(request_data['broadcaster_port']),
                                                   tx_message)
                                print(
                                    f"Sent {number_of_transactions} missing transactions to {request_data['broadcaster_host']}:{request_data['broadcaster_port']}")
                        else:
                            tx_message = {
                                'type': "TEST_MESSAGE",
                                'message': 'No missing transactions',
                                'timestamp': time.time()
                            }
                            self._send_to_peer(request_data['broadcaster_host'], int(request_data['broadcaster_port']),
                                               tx_message)

                else:
                    block_message = {
                        'type': "TEST_MESSAGE",
                        'message': 'Unknown tx hash',
                        'timestamp': time.time()
                        }
                    self._send_to_peer(request_data['broadcaster_host'], int(request_data['broadcaster_port']), block_message)










