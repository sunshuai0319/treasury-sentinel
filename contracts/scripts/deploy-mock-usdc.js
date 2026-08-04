const { ethers } = require("hardhat");

function units(value) {
  return ethers.parseUnits(value, 6);
}

async function main() {
  const [deployer] = await ethers.getSigners();
  const mintTo = process.env.MINT_TO || deployer.address;
  const mintAmount = process.env.MINT_AMOUNT_USDC || "1000";

  const usdc = await ethers.deployContract("MockUSDC");
  await usdc.waitForDeployment();
  const mintTx = await usdc.mint(mintTo, units(mintAmount));
  await mintTx.wait();

  console.log(
    JSON.stringify({
      mockUSDC: await usdc.getAddress(),
      deployer: deployer.address,
      mintedTo: mintTo,
      mintedAmountUSDC: mintAmount,
      mintTx: mintTx.hash,
    })
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

