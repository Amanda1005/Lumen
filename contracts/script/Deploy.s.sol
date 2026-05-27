// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {LumenScoringRegistry} from "../src/LumenScoringRegistry.sol";

contract DeployScript is Script {
    function run() external returns (LumenScoringRegistry registry) {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deployer:", deployer);
        console.log("Balance:", deployer.balance);

        vm.startBroadcast(deployerPrivateKey);
        registry = new LumenScoringRegistry(deployer);
        vm.stopBroadcast();

        console.log("LumenScoringRegistry deployed to:", address(registry));
    }
}