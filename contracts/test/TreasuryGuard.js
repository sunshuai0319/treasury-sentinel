const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("TreasuryGuard", function () {
  async function deployFixture() {
    const [admin, recipient, guardian, outsider] = await ethers.getSigners();
    const usdc = await ethers.deployContract("MockUSDC");
    const guard = await ethers.deployContract("TreasuryGuard", [admin.address, 500_000_000]);
    await guard.setTokenAllowed(await usdc.getAddress(), true);
    await usdc.mint(await guard.getAddress(), 1_000_000_000);
    const guardianRole = await guard.GUARDIAN_ROLE();
    await guard.grantRole(guardianRole, guardian.address);
    return { recipient, guardian, outsider, usdc, guard };
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

  it("blocks unlisted tokens and enforces vendor and daily limits", async function () {
    const { recipient, usdc, guard } = await deployFixture();
    const otherToken = await ethers.deployContract("MockUSDC");
    const vendorId = ethers.id("vendor-1");
    await guard.setRecipientAllowed(recipient.address, true);
    await guard.setVendorLimit(vendorId, 600_000_000);
    await guard.setDailyLimit(800_000_000);

    await expect(
      guard.executePaymentWithVendor(otherToken, recipient.address, 1, ethers.id("INV-X"), vendorId, ethers.id("dX"))
    ).to.be.revertedWithCustomError(guard, "TokenNotAllowed");

    await guard.executePaymentWithVendor(
      await usdc.getAddress(),
      recipient.address,
      400_000_000,
      ethers.id("INV-5"),
      vendorId,
      ethers.id("d5")
    );
    await expect(
      guard.executePaymentWithVendor(
        await usdc.getAddress(),
        recipient.address,
        300_000_000,
        ethers.id("INV-6"),
        vendorId,
        ethers.id("d6")
      )
    ).to.be.revertedWithCustomError(guard, "VendorLimitExceeded");

    await expect(
      guard.executePaymentWithVendor(
        await usdc.getAddress(),
        recipient.address,
        500_000_000,
        ethers.id("INV-7"),
        ethers.id("vendor-2"),
        ethers.id("d7")
      )
    ).to.be.revertedWithCustomError(guard, "DailyLimitExceeded");
  });

  it("allows guardians to pause but only admins to unpause", async function () {
    const { recipient, guardian, outsider, usdc, guard } = await deployFixture();
    await guard.setRecipientAllowed(recipient.address, true);
    await guard.connect(guardian).pause();

    await expect(
      guard.executePayment(await usdc.getAddress(), recipient.address, 1, ethers.id("INV-4"), ethers.id("d4"))
    ).to.be.revertedWithCustomError(guard, "EnforcedPause");

    await expect(guard.connect(outsider).unpause()).to.be.reverted;
    await guard.unpause();
  });
});
