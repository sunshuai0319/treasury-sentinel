// 调高 TreasuryGuard 每日限额(admin 操作)。
// 用法:MINT_DAILY_LIMIT_USDC=5000 npx hardhat run scripts/set-daily-limit.js --network baseSepolia
require("dotenv").config({ path: ".env", quiet: true });
const { ethers } = require("hardhat");

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

async function main() {
  const provider = new ethers.JsonRpcProvider(requiredEnv("BASE_SEPOLIA_RPC_URL"));
  const deployer = new ethers.Wallet(requiredEnv("DEPLOYER_PRIVATE_KEY"), provider);
  const treasuryGuardAddress = requiredEnv("TREASURY_GUARD_ADDRESS");
  const limitUsdc = process.env.DAILY_LIMIT_USDC || "5000";

  const guard = new ethers.Contract(
    treasuryGuardAddress,
    [
      "function setDailyLimit(uint256 limitUnits) external",
      "function dailyLimitUnits() view returns (uint256)",
    ],
    deployer
  );
  const tx = await guard.setDailyLimit(ethers.parseUnits(limitUsdc, 6));
  await tx.wait();
  const newLimit = await guard.dailyLimitUnits();
  console.log(
    JSON.stringify({
      deployer: deployer.address,
      treasuryGuard: treasuryGuardAddress,
      dailyLimitUSDC: ethers.formatUnits(newLimit, 6),
      tx: tx.hash,
    })
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
