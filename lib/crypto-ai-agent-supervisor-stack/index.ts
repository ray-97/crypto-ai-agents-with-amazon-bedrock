// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as managedblockchain from 'aws-cdk-lib/aws-managedblockchain';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as pythonLambda from '@aws-cdk/aws-lambda-python-alpha';
import * as ecrAssets from 'aws-cdk-lib/aws-ecr-assets';
import { bedrock as bedrockGenAIConstructs} from '@cdklabs/generative-ai-cdk-constructs';
import * as path from 'path';
import { getConfig, EnvironmentConfig } from '../../utils/environment';
const config: EnvironmentConfig = getConfig();

interface CryptoAIAgentSupervisorStackProps extends cdk.StackProps {
  knowledgeBase: bedrockGenAIConstructs.KnowledgeBase;
}

export class CryptoAIAgentSupervisorStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: CryptoAIAgentSupervisorStackProps) {
    super(scope, id, props);

    // Create KMS wallet
    const kmsWallet = new cdk.aws_kms.Key(this, 'KmsWallet', {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      alias: 'crypto-ai-agent-wallet',
      keySpec: cdk.aws_kms.KeySpec.ECC_SECG_P256K1, // Use secp256k1 curve for Ethereum compatibility
      keyUsage: cdk.aws_kms.KeyUsage.SIGN_VERIFY
    });

    // Create accessor token for Managed Blockchain
    const accessorToken = new managedblockchain.CfnAccessor(this, 'AMBAccessorToken', {
      accessorType: "BILLING_TOKEN",
      networkType: 'POLYGON_MAINNET',
    });

    const agent = new bedrockGenAIConstructs.Agent(this, 'Agent', {
      name: 'CryptoAI_Supervisor_Agent',
      foundationModel: bedrockGenAIConstructs.BedrockFoundationModel.AMAZON_NOVA_LITE_V1,
      shouldPrepareAgent: true,
      enableUserInput: true,
      aliasName: 'CryptoAIAgent_v1',
      instruction: `
        Role: You are a Crypto AI Agent. You have access to an Ethereum Virtual Machine compatible blockchain and can query it and send transactions from your own wallet. You can query the blockchain for information and perform actions such as sending transactions. You have access to knowledge bases that contain information about the latest blockchain news and historic blockchain transactional data. You have access to a wallet that you can use to send transactions to the blockchain. Use the Action Group to interact with the blockchain.

        These are the functions you can invoke:
        sendTx - send a transaction to the blockchain
        estimateGas - estimate the gas cost of a transaction
        getBalance - get the balance of a wallet
        getCryptoPrice - get the price of a cryptocurrency token
        investAdviceMetric - get investment advice
        getWalletAddress - get your own wallet's address
      `,

    });

    agent.addKnowledgeBase(props.knowledgeBase);

    const baseEnvironment = {
      AMB_ACCESSOR_TOKEN: accessorToken.getAtt('BillingToken').toString(),
      COINGECKO_API_KEY: config.coinGeckoAPIKey,
    };

    const lambdaEnvironment = {
      ...baseEnvironment,
      ...(config.blockchainRPCURL && {
        BLOCKCHAIN_RPC_URL: process.env.BLOCKCHAIN_RPC_URL
      }),
    };

    const actionGroupWalletManagerFunction = new lambda.DockerImageFunction(this, 'WalletManagerActionGroupFunction', {
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, 'lambda'), {
        cmd: ['index.lambda_handler'],
        platform: ecrAssets.Platform.LINUX_AMD64,
      }),
      timeout: cdk.Duration.seconds(300),
      environment: lambdaEnvironment,
    });

    const actionGroupInvestmentAdviceFunction = new lambda.DockerImageFunction(this, 'InvestmentAdviceActionGroupFunction', {
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, 'lambda'), {
        cmd: ['index.lambda_handler'],
        platform: ecrAssets.Platform.LINUX_AMD64,
      }),
      timeout: cdk.Duration.seconds(300),
      environment: {
        AMB_ACCESSOR_TOKEN: accessorToken.getAtt('BillingToken').toString(),
        COINGECKO_API_KEY: config.coinGeckoAPIKey
      },
    });

    // This will grant all required permissions including DescribeKey
    kmsWallet.grant(actionGroupWalletManagerFunction, 
      'kms:DescribeKey',
      'kms:Encrypt',
      'kms:Decrypt',
      'kms:GetPublicKey'
    );

    kmsWallet.grant(actionGroupInvestmentAdviceFunction,
      'kms:DescribeKey',
      'kms:Encrypt',
      'kms:Decrypt',
      'kms:GetPublicKey'
    );

    const actionGroupInvestmentAdvice = new bedrockGenAIConstructs.AgentActionGroup(this, 'InvestmentAdvice', {
        actionGroupName: 'investment_advice',
        description: 'Get investment advice and get token prices',
        actionGroupExecutor: {
            lambda: actionGroupWalletManagerFunction
        },
        actionGroupState: "ENABLED",
        functionSchema: {
          functions: [{
            "description": "This function is used to get investment advice",
            "name": "investAdviceMetric",
            "parameters": {}
          },
          {
            "description": "This function is used to get the price of crypto tokens",
            "name": "getCryptoPrice",
            "parameters": {
                "token": {
                  "type": "string",
                  "description": "The token for which to get the price of",
                  "required": true
                },
            }
          },
                    {
            "description": "This function is used to get the agent's wallet address",
            "name": "getWalletAddress",
            "parameters": {}
          }
        ]
        }
    });

    const actionGroupWalletManagement = new bedrockGenAIConstructs.AgentActionGroup(this, 'WalletManagement', {
        actionGroupName: 'wallet_management',
        description: 'Queries the wallet address, gets wallet token balances, and sends ether to a specified address',
        actionGroupExecutor: {
            lambda: actionGroupInvestmentAdviceFunction
        },
        actionGroupState: "ENABLED",
        functionSchema: {
          functions: [{
            "description": "This function is used to lend assets on-chain and query individual address balances",
            "name": "getBalance",
            "parameters": {
                "walletAddress": {
                  "type": "string",
                  "description": "The walletAddress for which to query the balance",
                  "required": true
                },
            }
          },
          {
            "description": "This function is used to estimate the gas required for a payment transaction",
            "name": "estimateGas",
            "parameters": {}
          },
          {
            "description": "This function is used to send transactions",
            "name": "sendTx",
            "parameters": {
                "amount": {
                  "type": "string",
                  "description": "The amount of the currency to send",
                  "required": true
                },
                "receiver": {
                  "type": "string",
                  "description": "The wallet address to send the transaction to",
                  "required": true
                },
            }
          }]
        }
      });

      agent.addActionGroup(actionGroupWalletManagement);
      agent.addActionGroup(actionGroupInvestmentAdvice);

  }
}

