import { test, expect } from "@playwright/test";

test("demo console exposes the five fixed scenarios", async ({ page }) => {
  await page.goto("/demo");
  await expect(page.getByRole("button", { name: /Normal/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Duplicate/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Wallet mismatch/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Over limit/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Emergency pause/ })).toBeVisible();
});

test("new payment flow submits a request and renders analysis", async ({ page }) => {
  await page.route("**/api/payment-requests", async (route) => {
    await route.fulfill({
      json: {
        request_id: "pay_web_test",
        vendor_id: "vendor_demo",
        invoice_id: "inv_demo_001",
        amount_units: 420000000,
        recipient_address: "0x1111111111111111111111111111111111111111",
        status: "SUBMITTED",
        final_action: null,
        decision_hash: null,
        keeperhub_execution_id: null,
        transaction_hash: null
      }
    });
  });
  await page.route("**/api/payment-requests/pay_web_test/analyze", async (route) => {
    await route.fulfill({
      json: {
        request_id: "pay_web_test",
        scenario: "workflow",
        invoice_id: "inv_demo_001",
        vendor_id: "vendor_demo",
        final_action: "APPROVE",
        timeline: [
          {
            actor: "primary",
            action: "APPROVE",
            confidence: 0.72,
            reasons: ["primary checked policy"],
            policy_refs: ["payment-policy#2.1"]
          },
          {
            actor: "critic",
            action: "REVIEW",
            confidence: 0.78,
            reasons: ["critic challenged"],
            policy_refs: ["payment-policy#2.1"]
          },
          {
            actor: "final",
            action: "APPROVE",
            confidence: 1,
            reasons: ["rules allow"],
            policy_refs: ["payment-policy#2.1"]
          }
        ]
      }
    });
  });

  await page.goto("/payments/new");
  await page.getByRole("button", { name: /Submit demo payment/ }).click();
  await expect(page.getByText("Final action: APPROVE")).toBeVisible();
  await expect(page.getByText("rules allow")).toBeVisible();
});
