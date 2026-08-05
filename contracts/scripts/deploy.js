const hre = require("hardhat");
const { ethers } = hre;
const fs = require("fs");
const path = require("path");

function artifactHash(artifact) {
  return ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify(artifact.abi)));
}

async function main() {
  const [deployer] = await ethers.getSigners();
  const guard = await ethers.deployContract("TreasuryGuard", [deployer.address, 500_000_000]);
  await guard.waitForDeployment();
  const demoUsdcAddress = process.env.MOCK_USDC_ADDRESS || process.env.DEMO_USDC_ADDRESS;
  if (demoUsdcAddress) {
    const allowTokenTx = await guard.setTokenAllowed(demoUsdcAddress, true);
    await allowTokenTx.wait();
  }
  const deploymentTx = guard.deploymentTransaction();
  const receipt = deploymentTx ? await deploymentTx.wait() : null;
  const network = await ethers.provider.getNetwork();
  const artifact = await hre.artifacts.readArtifact("TreasuryGuard");
  const record = {
    contract: "TreasuryGuard",
    address: await guard.getAddress(),
    deployer: deployer.address,
    chainId: Number(network.chainId),
    network: network.name,
    deploymentTxHash: deploymentTx ? deploymentTx.hash : null,
    deploymentBlockNumber: receipt ? receipt.blockNumber : null,
    maxSinglePaymentUnits: "500000000",
    dailyLimitUnits: "2000000000",
    allowedTokenSeeded: demoUsdcAddress || null,
    abiHash: artifactHash(artifact),
  };
  const outputDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(outputDir, { recursive: true });
  if (network.chainId === 84532n) {
    fs.writeFileSync(path.join(outputDir, "base-sepolia.json"), JSON.stringify(record, null, 2));
  }
  console.log(JSON.stringify({ treasuryGuard: record.address, deployer: deployer.address }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
