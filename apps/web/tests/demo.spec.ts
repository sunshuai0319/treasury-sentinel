import { test, expect } from "@playwright/test";

test("demo console exposes the five fixed scenarios", async ({ page }) => {
  await page.goto("/demo");
  await expect(page.getByRole("button", { name: /Normal/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Duplicate/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Wallet mismatch/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Over limit/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Emergency pause/ })).toBeVisible();
});
