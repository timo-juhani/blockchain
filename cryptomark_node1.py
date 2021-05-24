#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
blockchain.py: Defines a Blockchain class that allows to initiate a new
Blockchain, append new blocks to it and validate the chain. An instance of
the Blockchain class is exposed through web API that is implemented using
Flask. 
"""

# Imports
import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

# Blockchain class


class Blockchain:
    """Blockchain class is used to create a new Blockchain and manage it."""

    def __init__(self):
        """ 
        chain is the list in which the Blockchain will be stored. 
        create_block, when called here, creates the first (genesis) block
        of the Blockchain.
        """

        self.chain = []
        self.transactions = []
        self.create_block(proof=1, previous_hash="0")
        self.nodes = set()

    def create_block(self, proof, previous_hash):
        """
        create_block method enables adding new blocks to the chain.    
        block stores the contents of a block in a dictionary.
        """

        block = {
            "index": len(self.chain)+1,
            "timestamp": str(datetime.datetime.now()),
            "proof": proof,
            "previous_hash": previous_hash,
            "transactions": self.transactions
        }
        # Blocks cannot contain overlapping transactions
        self.transactions = []
        self.chain.append(block)
        return block

    def get_previous_block(self):
        """get_previous_block returns the last item from the chain (list)"""
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        """
        Calculates the proof of work for a block to be added in the chain
        """
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(
                str(new_proof**2-previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == "0000":
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        """
        Provides the hash value of the block.
        """
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        """
        Validates whether the chain is the longest / latest.
        """
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block["previous_hash"] != self.hash(previous_block):
                return False
            previous_proof = previous_block["proof"]
            proof = block["proof"]
            hash_operation = hashlib.sha256(
                str(proof**2-previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != "0000":
                return False
            previous_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, receiver, amount):
        """
        Adds a new transaction to a block
        """
        self.transactions.append({
            "sender": sender,
            "receiver": receiver,
            "amount": amount
        })
        previous_block = self.get_previous_block()
        return previous_block["index"]+1

    def add_node(self, address):
        """
        Allows adding new nodes to the block chain
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        """
        Replaces the block chain with the longest version
        """
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f"http://{node}/get_chain")
            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        # if longest_chain not none and chain was replaced
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

# Expose the block chain via Flask web app
app = Flask(__name__)

# Creating nodes
node_address = str(uuid4()).replace("-","")

# Instantiate Blockchain
blockchain = Blockchain()

@app.route("/mine_block", methods=["GET"])
def mine_block():
    """
    Mines a new block for transactions
    """
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block["proof"]
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)
    blockchain.add_transaction(sender = node_address, receiver = "node1", amount = "1")
    response = {
        "message": "New block has been mined succesfully!",
        "index": block["index"],
        "timestamp": block["timestamp"],
        "proof": block["proof"],
        "previous_hash": block["previous_hash"],
        "transactions": block["transactions"]
    }
    return jsonify(response), 200


@app.route("/get_chain", methods=["GET"])
def get_chain():
    """
    Displays the current chain on a node.
    """
    response = {
        "chain": blockchain.chain,
        "length": len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route("/is_valid", methods=["GET"])
def is_valid():
    """
    Calls for blockchain validation.
    """
    chain = blockchain.chain
    if blockchain.is_chain_valid(chain):
        response = {
            "message": "OK! The chain is valid!"
        }
    else:
        response = {
            "message": "ERROR! The chain is invalid!"
        }
    return jsonify(response), 200

@app.route("/add_transaction", methods = ["POST"])
def add_transaction():
    """
    Adds a new transaction to blockchain
    """
    json = request.get_json()
    transaction_keys = ["sender", "receiver", "amount"]
    if not all (key in json for key in transaction_keys):
        return "Invalid transaction keys", 400
    index = blockchain.add_transaction(json["sender"], json["receiver"], json["amount"])
    response = {
            "message": f"Transaction will be added to block {index}"
        }
    return jsonify(response), 201

@app.route("/connect_node", methods = ["POST"])
def connect_node():
    """
    Connects the node to a decentralized P2P network.
    """
    json = request.get_json()
    nodes = json.get("nodes")
    if nodes is None:
        return "No nodes registered.", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {
            "message": "Nodes are connected",
            "total_nodes": list(blockchain.nodes) 
        }
    return jsonify(response), 201 

@app.route("/replace_chain", methods=["GET"])
def replace_chain():
    """
    Replace the chain by the longest chain if needed
    """
    if blockchain.replace_chain():
        response = {
            "message": "Chain was replaced by the longest one!",
            "new_chain": blockchain.chain
        }
    else:
        response = {
            "message": "Chain is the longest one. Not replaced.",
            "current_chain": blockchain.chain
        }
    return jsonify(response), 200

# Run the blockchain as a web application on a node
app.run(host="0.0.0.0", port=5001)
