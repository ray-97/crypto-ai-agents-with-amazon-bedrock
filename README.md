# Autonomous Crypto Portfolio Rebalancer Agent

## Project Overview

This project demonstrates an autonomous crypto portfolio rebalancing agent built using **AWS Bedrock's AI capabilities** and powered by **Chainlink's decentralized services**. The goal is to create a robust and intelligent system that can monitor a cryptocurrency portfolio and automatically trigger rebalancing actions when predefined conditions are met, ensuring the portfolio adheres to target allocations.

This project is a submission for the Chainlink Chrominon Hackathon, showcasing the integration of advanced AI with on-chain automation and data.

## Accomplishments & Current Features

We have successfully set up the foundational infrastructure and implemented the core automation pipeline, enabling a powerful integration between off-chain AI and on-chain blockchain events.

### 1. **AWS Bedrock AI Agent Infrastructure**
   * **Deployment:** Successfully deployed a multi-agent system on AWS Bedrock, including a **Supervisor Agent** (the main "Crypto AI Agent") and a **Collaborator Agent** (for "Blockchain Data" queries).
   * **Configuration:** Configured Bedrock model access for `Amazon Nova Pro v1` (or equivalent Claude 3) and `Amazon Titan Embeddings G1 - Textv1.2`.
   * **Basic Interaction:** The Supervisor Agent is configured to respond to queries and delegate tasks (e.g., wallet address queries, basic blockchain data fetches) to its collaborator via action groups.
   * **Secure Wallet Integration:** The agent is integrated with a secure wallet whose private key is managed by **AWS Key Management Service (KMS)**, allowing it to prepare and sign transactions (though full DEX swap logic is a future enhancement).

### 2. **Chainlink-Powered On-Chain Automation & Data**

   * **Hardhat Development Environment:** Established a Hardhat project for Solidity smart contract development, integrated with Chainlink libraries.
   * **`PriceConsumerV3.sol` (Chainlink Data Feed Consumer):** Deployed a smart contract to **Sepolia Testnet** that can query and retrieve real-time asset prices (e.g., ETH/USD) using **Chainlink Data Feeds**. This provides the foundation for accurate portfolio valuation.
   * **`RebalancerKeeper.sol` (Chainlink Automation-Compatible Contract):**
     * Deployed a custom smart contract to **Sepolia Testnet** that implements the `KeeperCompatibleInterface` with `checkUpkeep` and `performUpkeep` functions.
     * This contract is designed to eventually hold the logic for detecting portfolio imbalance based on real-time Chainlink Price Feeds and actual wallet holdings.
     * **Current State for Demo:** For initial demonstration and testing purposes, the `checkUpkeep` logic has been simplified to reliably return `true` to ensure the `performUpkeep` function is triggered by Chainlink Automation.
     * **Event Emission:** The `performUpkeep` function successfully emits a `RebalanceRequested` event when triggered.
   * **Chainlink Automation Upkeep:** Registered an active **Custom Logic Upkeep** on the **Sepolia Testnet** for the `RebalancerKeeper` contract. This ensures Chainlink's decentralized network periodically evaluates the contract's `checkUpkeep` function and triggers `performUpkeep` when conditions are met.

### 3. **AWS Lambda Event Listener (The Bridge)**

   * **`RebalancerAutomationListener` Lambda Function:** Developed and deployed an AWS Lambda function responsible for bridging the on-chain Chainlink events with the off-chain AWS Bedrock agent.
   * **Event Polling:** The Lambda function is configured via an **Amazon EventBridge (CloudWatch Events) schedule** to periodically poll the Sepolia blockchain for new `RebalanceRequested` events emitted by the `RebalancerKeeper` contract.
   * **Bedrock Agent Invocation:** Upon detecting a `RebalanceRequested` event, the Lambda successfully invokes the AWS Bedrock Supervisor Agent, passing relevant details (e.g., portfolio address, deviation) as part of a prompt.
   * **IAM Permissions:** Configured necessary IAM roles and policies to allow the Lambda to read blockchain data (via RPC), write logs to CloudWatch, and invoke the Bedrock Agent.

## Technologies Used

* **AWS Bedrock:** For generative AI agents (Supervisor and Collaborator), knowledge bases, and agent runtime.
* **AWS Lambda:** Serverless compute for event listeners and agent action groups.
* **AWS KMS:** For secure management of cryptographic keys (agent's wallet private key).
* **AWS CloudFormation / CDK:** For Infrastructure as Code deployment of AWS resources.
* **Chainlink Automation:** For decentralized, reliable triggers based on custom on-chain logic.
* **Chainlink Data Feeds:** For real-time, decentralized price data on-chain.
* **Solidity:** Smart contract language.
* **Hardhat:** Ethereum development environment for compiling, testing, and deploying smart contracts.
* **Ethers.js / Web3.py:** Libraries for blockchain interaction in JavaScript (Hardhat) and Python (Lambda).
* **Sepolia Testnet:** The target blockchain network for contract deployment and Chainlink services.

## Setup & Deployment Instructions

Refer to the project's documentation and the `scripts/` directory for detailed instructions on:

* Setting up your AWS CLI and AWS CDK environment.
* Cloning the repository and configuring environment variables (`.env` files).
* Installing Node.js dependencies.
* Deploying the AWS Bedrock agent infrastructure via `cdk deploy --all`.
* Configuring Bedrock console settings (model access, agent aliases, knowledge base sync).
* Deploying the `PriceConsumerV3.sol` and `RebalancerKeeper.sol` contracts to Sepolia.
* Acquiring Sepolia testnet ETH and LINK tokens.
* Registering the `RebalancerKeeper` contract as a Custom Logic Upkeep on the Chainlink Automation App.
* Configuring and deploying the `RebalancerAutomationListener` AWS Lambda function.