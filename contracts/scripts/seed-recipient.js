const { ethers } = require("hardhat");

const DEFAULT_DEMO_RECIPIENT = "0x1111111111111111111111111111111111111111";

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

async function main() {
  const [deployer] = await ethers.getSigners();
  const treasuryGuardAddress = requiredEnv("TREASURY_GUARD_ADDRESS");
  const recipient =
    argValue("--recipient") ||
    process.env.RECIPIENT_ADDRESS ||
    process.env.VENDOR_WALLET_ADDRESS ||
    DEFAULT_DEMO_RECIPIENT;

  if (!ethers.isAddress(recipient)) {
    throw new Error(`Invalid recipient address: ${recipient}`);
  }

  const guard = await ethers.getContractAt("TreasuryGuard", treasuryGuardAddress);
  const alreadyAllowed = await guard.allowedRecipients(recipient);
  let txHash = null;
  if (!alreadyAllowed) {
    const tx = await guard.setRecipientAllowed(recipient, true);
    await tx.wait();
    txHash = tx.hash;
  }

  console.log(
    JSON.stringify({
      deployer: deployer.address,
      treasuryGuard: treasuryGuardAddress,
      recipient,
      wasAlreadyAllowed: alreadyAllowed,
      allowedNow: await guard.allowedRecipients(recipient),
      tx: txHash,
    })
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
