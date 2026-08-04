const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("TreasuryGuard", function () {
  async function deployFixture() {
    const [admin, recipient] = await ethers.getSigners();
    const usdc = await ethers.deployContract("MockUSDC");
    const guard = await ethers.deployContract("TreasuryGuard", [admin.address, 500_000_000]);
    await usdc.mint(await guard.getAddress(), 1_000_000_000);
    return { recipient, usdc, guard };
  }

  it("executes a whitelisted payment once", async function () {
    const { recipient, usdc, guard } = await deployFixture();
    const invoiceHash = ethers.id("INV-1");
    const decisionHash = ethers.id("decision-1");

    await guard.setRecipientAllowed(recipient.address, true);
    await expect(
      guard.executePayment(await usdc.getAddress(), recipient.address, 420_000_000, invoiceHash, decisionHash)
    ).to.emit(guard, "PaymentExecuted");
    expect(await usdc.balanceOf(recipient.address)).to.equal(420_000_000);
    await expect(
      guard.executePayment(await usdc.getAddress(), recipient.address, 1, invoiceHash, decisionHash)
    ).to.be.revertedWithCustomError(guard, "InvoiceAlreadyPaid");
  });

  it("blocks unlisted recipients and over-limit payments", async function () {
    const { recipient, usdc, guard } = await deployFixture();

    await expect(
      guard.executePayment(await usdc.getAddress(), recipient.address, 1, ethers.id("INV-2"), ethers.id("d2"))
    ).to.be.revertedWithCustomError(guard, "RecipientNotAllowed");

    await guard.setRecipientAllowed(recipient.address, true);
    await expect(
      guard.executePayment(await usdc.getAddress(), recipient.address, 700_000_000, ethers.id("INV-3"), ethers.id("d3"))
    ).to.be.revertedWithCustomError(guard, "PaymentTooLarge");
  });

  it("blocks execution while paused", async function () {
    const { recipient, usdc, guard } = await deployFixture();
    await guard.setRecipientAllowed(recipient.address, true);
    await guard.pause();

    await expect(
      guard.executePayment(await usdc.getAddress(), recipient.address, 1, ethers.id("INV-4"), ethers.id("d4"))
    ).to.be.revertedWithCustomError(guard, "EnforcedPause");
  });
});

