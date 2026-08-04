const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  const guard = await ethers.deployContract("TreasuryGuard", [deployer.address, 500_000_000]);
  await guard.waitForDeployment();
  console.log(JSON.stringify({ treasuryGuard: await guard.getAddress(), deployer: deployer.address }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

