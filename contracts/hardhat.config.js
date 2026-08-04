require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: ".env", quiet: true });

const deployerPrivateKey = process.env.DEPLOYER_PRIVATE_KEY || "";
const accounts = /^0x[0-9a-fA-F]{64}$/.test(deployerPrivateKey) ? [deployerPrivateKey] : [];

module.exports = {
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: { enabled: true, runs: 200 }
    }
  },
  networks: {
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_RPC_URL || "",
      accounts
    }
  }
};
