import os
import json
import time
from web3 import Web3
from web3.middleware import geth_filter
import boto3

# --- Environment Variables ---
WEB3_PROVIDER_URL = os.environ.get("WEB3_PROVIDER_URL") # Sepolia WS endpoint (wss://)
REBALANCER_KEEPER_CONTRACT_ADDRESS = os.environ.get("REBALANCER_KEEPER_CONTRACT_ADDRESS")
BEDROCK_AGENT_ID = os.environ.get("BEDROCK_AGENT_ID")
BEDROCK_AGENT_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID")
# You can also pass the agent's wallet address if needed for context
# KMS_AGENT_WALLET_ADDRESS = os.environ.get("KMS_AGENT_WALLET_ADDRESS")

# --- Initialize Web3 and Bedrock Client (outside handler for warm starts) ---
w3 = None
bedrock_agent_runtime = None
last_block_processed = 0 # This will need to be persistent across invocations

# ABI for the RebalanceRequested event
# You can get this from your RebalancerKeeper.json artifact (in artifacts/contracts/)
# Look for the 'abi' field and find the event definition.
REBALANCER_KEEPER_ABI = json.loads('''
[
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "_ethUsdPriceFeedAddress",
          "type": "address"
        },
        {
          "internalType": "address",
          "name": "_portfolioManagerAddress",
          "type": "address"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "constructor"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "portfolio",
          "type": "address"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "currentDeviationBps",
          "type": "uint256"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "timestamp",
          "type": "uint256"
        }
      ],
      "name": "RebalanceRequested",
      "type": "event"
    },
    {
      "inputs": [],
      "name": "REBALANCE_THRESHOLD_PERCENT",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "bytes",
          "name": "checkData",
          "type": "bytes"
        }
      ],
      "name": "checkUpkeep",
      "outputs": [
        {
          "internalType": "bool",
          "name": "upkeepNeeded",
          "type": "bool"
        },
        {
          "internalType": "bytes",
          "name": "performData",
          "type": "bytes"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "getEthUsdPriceFeedAddress",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "getPortfolioManagerAddress",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "getRebalanceThreshold",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "lastRebalanceTimestamp",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "bytes",
          "name": "performData",
          "type": "bytes"
        }
      ],
      "name": "performUpkeep",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "portfolioManagerAddress",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    }
]
''') # Pasted from your RebalancerKeeper.json ABI

def initialize_clients():
    global w3, bedrock_agent_runtime
    if w3 is None:
        # Use HTTP provider for polling as Lambda's environment might not maintain WS
        w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL.replace("wss://", "https://")))
        # For a persistent listener (e.g., on EC2), you'd use WebSocketProvider
        # w3 = Web3(Web3.WebsocketProvider(WEB3_PROVIDER_URL))

    if bedrock_agent_runtime is None:
        bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")

    if not w3.is_connected():
        raise Exception("Failed to connect to web3 provider.")

def get_last_processed_block():
    # In a real application, store this in DynamoDB or S3 for persistence
    # For this example, we'll use a simple in-memory variable (will reset on cold start)
    # For production, implement a persistent store for `last_block_processed`
    # e.g., read from DynamoDB, update after processing events.
    return last_block_processed

def set_last_processed_block(block_number):
    global last_block_processed
    last_block_processed = block_number
    # In production, write this to DynamoDB

def lambda_handler(event, context):
    initialize_clients()

    current_block = w3.eth.block_number
    from_block = get_last_processed_block()
    if from_block == 0: # First run or cold start, start from a recent block
         from_block = current_block - 100 # Adjust history as needed

    print(f"Checking for events from block {from_block} to {current_block}")

    keeper_contract = w3.eth.contract(address=REBALANCER_KEEPER_CONTRACT_ADDRESS, abi=REBALANCER_KEEPER_ABI)

    # Get the RebalanceRequested event filter
    rebalance_event_filter = keeper_contract.events.RebalanceRequested.create_filter(
        fromBlock=from_block,
        toBlock=current_block
    )

    events = rebalance_event_filter.get_all_entries()

    if not events:
        print("No RebalanceRequested events found in this block range.")
    else:
        print(f"Found {len(events)} RebalanceRequested events.")
        for event_data in events:
            print(f"Processing event: {event_data}")
            portfolio_address = event_data['args']['portfolio']
            deviation_bps = event_data['args']['currentDeviationBps']
            event_timestamp = event_data['args']['timestamp']

            prompt_text = (
                f"Automated trigger from Chainlink Automation: Rebalancing required for portfolio {portfolio_address}. "
                f"Current deviation is {deviation_bps / 100:.2f} basis points. "
                f"Event occurred at timestamp {event_timestamp}. Please analyze and execute necessary rebalancing transactions."
            )

            print(f"Invoking Bedrock Agent for portfolio: {portfolio_address}")
            try:
                # Construct a unique session ID for each rebalance request
                session_id = f"rebalance_trigger_{portfolio_address}_{event_timestamp}_{time.time_ns()}"

                response = bedrock_agent_runtime.invoke_agent(
                    agentId=BEDROCK_AGENT_ID,
                    agentAliasId=BEDROCK_AGENT_ALIAS_ID,
                    sessionId=session_id,
                    inputText=prompt_text
                )

                # Read the response stream from the agent
                agent_response = ""
                for chunk in response['completion']:
                    if 'bytes' in chunk:
                        agent_response += chunk['bytes'].decode('utf-8')

                print(f"Bedrock Agent Response for {portfolio_address}: {agent_response}")

            except Exception as e:
                print(f"Error invoking Bedrock Agent for {portfolio_address}: {e}")
                # Implement robust error handling, e.g., send to DLQ, retry

    set_last_processed_block(current_block + 1) # Update last processed block

    return {
        'statusCode': 200,
        'body': json.dumps('Rebalancer Automation Listener executed.')
    }