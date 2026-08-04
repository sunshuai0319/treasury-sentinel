const { ethers } = require("hardhat");

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function units(value) {
  return ethers.parseUnits(value, 6);
}

async function main() {
  const [deployer] = await ethers.getSigners();
  const mockUsdcAddress = requiredEnv("MOCK_USDC_ADDRESS");
  const treasuryGuardAddress = requiredEnv("TREASURY_GUARD_ADDRESS");
  const mintAmount = process.env.MINT_AMOUNT_USDC || "1000";

  const code = await ethers.provider.getCode(mockUsdcAddress);
  if (code === "0x") {
    throw new Error(`No contract found at MOCK_USDC_ADDRESS=${mockUsdcAddress}`);
  }
  const usdc = await ethers.getContractAt("MockUSDC", mockUsdcAddress);
  const mintTx = await usdc.mint(treasuryGuardAddress, units(mintAmount));
  await mintTx.wait();
  const guardBalance = await usdc.balanceOf(treasuryGuardAddress);

  console.log(
    JSON.stringify({
      deployer: deployer.address,
      mockUSDC: mockUsdcAddress,
      treasuryGuard: treasuryGuardAddress,
      mintedAmountUSDC: mintAmount,
      guardBalanceUSDC: ethers.formatUnits(guardBalance, 6),
      mintTx: mintTx.hash,
    })
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
