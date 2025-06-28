// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@chainlink/contracts/src/v0.8/automation/interfaces/KeeperCompatibleInterface.sol";
import "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

/// @title RebalancerKeeper
/// @notice A Chainlink Automation compatible contract to check for portfolio imbalance
///         and trigger a rebalance event.
contract RebalancerKeeper is KeeperCompatibleInterface {
    AggregatorV3Interface internal ethUsdPriceFeed; // Example price feed
    // You might need more price feeds depending on your portfolio assets

    address public portfolioManagerAddress; // The address of the portfolio manager (e.g., your AWS Lambda's associated wallet/EOA)
    uint256 public constant REBALANCE_THRESHOLD_PERCENT = 5; // Rebalance if > 5% deviation
    uint256 public lastRebalanceTimestamp;

    // Event to be emitted when rebalance is needed, listened to by AWS Lambda
    event RebalanceRequested(address indexed portfolio, uint256 currentDeviationBps, uint256 timestamp);

    /// @notice Constructor for the RebalancerKeeper contract.
    /// @param _ethUsdPriceFeedAddress The address of the ETH/USD Chainlink Price Feed.
    /// @param _portfolioManagerAddress The address that manages the portfolio. This is typically your agent's associated wallet address.
    constructor(address _ethUsdPriceFeedAddress, address _portfolioManagerAddress) {
        ethUsdPriceFeed = AggregatorV3Interface(_ethUsdPriceFeedAddress);
        portfolioManagerAddress = _portfolioManagerAddress;
        lastRebalanceTimestamp = block.timestamp; // Initialize
    }

    /// @notice This function is called off-chain by Chainlink Automation nodes.
    ///         It checks if a rebalance condition is met.
    /// @param checkData An arbitrary byte array used to pass data to the checkUpkeep function. (Not used in this simple example).
    /// @return upkeepNeeded True if the upkeep conditions are met, false otherwise.
    /// @return performData An arbitrary byte array to be passed to the performUpkeep function.
    function checkUpkeep(bytes calldata checkData)
        external
        view
        override
        returns (bool upkeepNeeded, bytes memory performData)
    {
        // --- Step 1: Fetch current prices (using Chainlink Data Feeds) ---
        // In a real scenario, you'd fetch prices for ALL assets in your portfolio
        // using multiple price feeds.
        (, int256 ethPriceUsd, , ,) = ethUsdPriceFeed.latestRoundData();
        require(ethPriceUsd > 0, "Invalid ETH price from feed"); // Basic sanity check

        // --- Step 2: Simulate Portfolio State (Replace with actual portfolio query) ---
        // In a real application, you'd need to:
        // a) Query the portfolio's actual holdings for `portfolioManagerAddress`.
        // b) Get target allocations (e.g., from an immutable strategy or a configurable variable).
        // This example uses simple hardcoded values for demonstration.
        uint256 currentEthAmountUsd = 10000; // Example: $10,000 worth of ETH
        uint256 currentUsdcAmountUsd = 5000; // Example: $5,000 worth of USDC
        uint256 totalPortfolioValueUsd = currentEthAmountUsd + currentUsdcAmountUsd;

        // Target allocation example: 60% ETH, 40% USDC
        uint256 targetEthValueUsd = (totalPortfolioValueUsd * 60) / 100;
        uint256 targetUsdcValueUsd = (totalPortfolioValueUsd * 40) / 100;

        // Calculate current deviation from target (in basis points for simplicity)
        // This is a simplified deviation calculation. More robust methods exist.
        uint256 ethDeviationUsd = currentEthAmountUsd > targetEthValueUsd
            ? currentEthAmountUsd - targetEthValueUsd
            : targetEthValueUsd - currentEthAmountUsd;

        uint256 totalDeviationBps = (ethDeviationUsd * 10000) / totalPortfolioValueUsd; // Deviation in Basis Points

        // --- Step 3: Determine if rebalance is needed ---
        upkeepNeeded = (totalDeviationBps > REBALANCE_THRESHOLD_PERCENT * 100) &&
                       (block.timestamp > lastRebalanceTimestamp + 1 hours); // Example: Rebalance max once per hour

        // The performData can be used to pass information to performUpkeep
        // Here, we pass the calculated deviation
        performData = abi.encode(totalDeviationBps);
    }


    /// @notice This function is called on-chain by Chainlink Automation when upkeepNeeded is true.
    ///         It emits an event for the AWS Lambda to pick up.
    /// @param performData The byte array returned by checkUpkeep.
    function performUpkeep(bytes calldata performData) external override {
        // Re-check the condition to avoid race conditions, though Automation ensures this is usually safe.
        (bool upkeepNeeded, bytes memory _performData) = this.checkUpkeep(performData);
        require(upkeepNeeded, "No upkeep needed at this time.");

        uint256 currentDeviationBps = abi.decode(_performData, (uint256));

        // Emit an event that your AWS Lambda function will listen for.
        emit RebalanceRequested(portfolioManagerAddress, currentDeviationBps, block.timestamp);

        lastRebalanceTimestamp = block.timestamp; // Update last rebalance time
    }

    // --- Helper functions for Chainlink Automation Registration ---
    // These are often added for convenience during upkeep registration
    function getEthUsdPriceFeedAddress() public view returns (address) {
        return address(ethUsdPriceFeed);
    }

    function getPortfolioManagerAddress() public view returns (address) {
        return portfolioManagerAddress;
    }

    function getRebalanceThreshold() public view returns (uint256) {
        return REBALANCE_THRESHOLD_PERCENT;
    }
}