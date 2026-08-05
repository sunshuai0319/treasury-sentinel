const { ethers } = require("hardhat");

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function argValue(name) {
  const index = process.argv.indexOf(name);
  if (index === -1) return null;
  const value = process.argv[index + 1];
  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${name}`);
  }
  return value;
}

async function grantIfMissing(guard, role, roleName, wallet) {
  const alreadyGranted = await guard.hasRole(role, wallet);
  let txHash = null;
  let receiptStatus = null;
  if (!alreadyGranted) {
    const tx = await guard.grantRole(role, wallet);
    const receipt = await tx.wait();
    txHash = tx.hash;
    receiptStatus = receipt ? receipt.status : null;
  }
  const finalGranted = await guard.hasRole(role, wallet);
  return {
    roleName,
    role,
    alreadyGranted,
    grantedNow: finalGranted,
    tx: txHash,
    receiptStatus,
  };
}

async function main() {
  const [deployer] = await ethers.getSigners();
  const treasuryGuardAddress = requiredEnv("TREASURY_GUARD_ADDRESS");
  const wallet =
    argValue("--wallet") ||
    process.env.KEEPERHUB_WALLET_ADDRESS ||
    process.env.EXECUTOR_WALLET_ADDRESS;
  const grantGuardian = process.argv.includes("--guardian") || process.env.GRANT_GUARDIAN_ROLE === "true";

  if (!wallet) {
    throw new Error("Missing KeeperHub wallet. Set KEEPERHUB_WALLET_ADDRESS or pass --wallet 0x...");
  }
  if (!ethers.isAddress(wallet)) {
    throw new Error(`Invalid wallet address: ${wallet}`);
  }

  const guard = await ethers.getContractAt("TreasuryGuard", treasuryGuardAddress);
  const executorRole = await guard.EXECUTOR_ROLE();
  const grants = [await grantIfMissing(guard, executorRole, "EXECUTOR_ROLE", wallet)];
  if (grantGuardian) {
    const guardianRole = await guard.GUARDIAN_ROLE();
    grants.push(await grantIfMissing(guard, guardianRole, "GUARDIAN_ROLE", wallet));
  }

  console.log(
    JSON.stringify({
      deployer: deployer.address,
      treasuryGuard: treasuryGuardAddress,
      keeperhubWallet: wallet,
      grants,
    })
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
