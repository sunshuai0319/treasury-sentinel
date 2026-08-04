const { ethers } = require("hardhat");

function formatUsdc(amount) {
  return ethers.formatUnits(amount, 6);
}

async function expectRevert(label, action) {
  try {
    await action();
  } catch (error) {
    const message = error.shortMessage || error.message || String(error);
    console.log(JSON.stringify({ check: label, ok: true, reverted: message }));
    return;
  }
  throw new Error(`${label} did not revert`);
}

async function main() {
  const [admin, recipient, stranger] = await ethers.getSigners();
  const amount = 420_000_000;
  const maxSinglePaymentUnits = 500_000_000;
  const invoiceHash = ethers.id("LOCAL-DEMO-INVOICE-001");
  const decisionHash = ethers.id("LOCAL-DEMO-DECISION-001");

  const usdc = await ethers.deployContract("MockUSDC");
  await usdc.waitForDeployment();

  const guard = await ethers.deployContract("TreasuryGuard", [
    admin.address,
    maxSinglePaymentUnits,
  ]);
  await guard.waitForDeployment();

  await (await usdc.mint(await guard.getAddress(), 1_000_000_000)).wait();
  await (await guard.setRecipientAllowed(recipient.address, true)).wait();

  const beforeBalance = await usdc.balanceOf(recipient.address);
  const tx = await guard.executePayment(
    await usdc.getAddress(),
    recipient.address,
    amount,
    invoiceHash,
    decisionHash
  );
  const receipt = await tx.wait();
  const afterBalance = await usdc.balanceOf(recipient.address);

  await expectRevert("duplicate invoice is blocked", async () =>
    guard.executePayment(await usdc.getAddress(), recipient.address, 1, invoiceHash, decisionHash)
  );

  await expectRevert("unlisted recipient is blocked", async () =>
    guard.executePayment(
      await usdc.getAddress(),
      stranger.address,
      1,
      ethers.id("LOCAL-DEMO-INVOICE-002"),
      ethers.id("LOCAL-DEMO-DECISION-002")
    )
  );

  await expectRevert("over-limit payment is blocked", async () =>
    guard.executePayment(
      await usdc.getAddress(),
      recipient.address,
      700_000_000,
      ethers.id("LOCAL-DEMO-INVOICE-003"),
      ethers.id("LOCAL-DEMO-DECISION-003")
    )
  );

  await (await guard.pause()).wait();
  await expectRevert("paused contract blocks execution", async () =>
    guard.executePayment(
      await usdc.getAddress(),
      recipient.address,
      1,
      ethers.id("LOCAL-DEMO-INVOICE-004"),
      ethers.id("LOCAL-DEMO-DECISION-004")
    )
  );

  console.log(
    JSON.stringify(
      {
        network: (await ethers.provider.getNetwork()).name,
        chainId: Number((await ethers.provider.getNetwork()).chainId),
        admin: admin.address,
        recipient: recipient.address,
        mockUSDC: await usdc.getAddress(),
        treasuryGuard: await guard.getAddress(),
        paymentTx: receipt.hash,
        blockNumber: receipt.blockNumber,
        recipientBalanceBefore: formatUsdc(beforeBalance),
        recipientBalanceAfter: formatUsdc(afterBalance),
        paidInvoiceRecorded: await guard.paidInvoiceHashes(invoiceHash),
        paused: await guard.paused(),
      },
      null,
      2
    )
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
