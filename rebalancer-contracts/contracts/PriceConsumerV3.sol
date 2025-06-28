// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

contract PriceConsumerV3 {
    AggregatorV3Interface internal priceFeed;

    /// @notice Constructor sets the address of the Chainlink Price Feed.
    /// @param _priceFeedAddress The address of the AggregatorV3Interface contract.
    constructor(address _priceFeedAddress) {
        priceFeed = AggregatorV3Interface(_priceFeedAddress);
    }

    /// @notice Returns the latest price from the Chainlink Price Feed.
    /// @dev Returns price with 8 decimals (e.g., 2000000000 for $2000).
    function getLatestPrice() public view returns (int256) {
        // Check Chainlink documentation for function return values
        // https://docs.chain.link/data-feeds/price-feeds/api-reference#latestrounddata
        (
            /*uint80 roundID*/,
            int256 price,
            /*uint startedAt*/,
            /*uint timeStamp*/,
            /*uint80 answeredInRound*/
        ) = priceFeed.latestRoundData();
        return price;
    }

    /// @notice Returns the Chainlink Price Feed address used by this contract.
    function getPriceFeedAddress() public view returns (address) {
        return address(priceFeed);
    }
}