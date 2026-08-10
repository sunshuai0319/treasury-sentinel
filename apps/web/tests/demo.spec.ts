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
  let eventRequests = 0;
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
      status: 202,
      json: {
        request_id: "pay_web_test",
        invoice_id: "inv_demo_001",
        vendor_id: "vendor_demo",
        amount_units: 420000000,
        recipient_address: "0x1111111111111111111111111111111111111111",
        status: "ANALYZING",
        final_action: null,
        decision_hash: null,
        keeperhub_execution_id: null,
        transaction_hash: null
      }
    });
  });
  await page.route("**/api/payment-requests/pay_web_test/events**", async (route) => {
    eventRequests += 1;
    const stream = [
      'id: run_web_test:0\nevent: primary\ndata: {"actor":"primary","action":"APPROVE","confidence":0.72,"reasons":["primary checked policy"],"policy_refs":["payment-policy#2.1"]}\n\n',
      'id: run_web_test:1\nevent: critic\ndata: {"actor":"critic","action":"REVIEW","confidence":0.78,"reasons":["critic challenged"],"policy_refs":["payment-policy#2.1"]}\n\n',
      'id: run_web_test:2\nevent: final\ndata: {"actor":"final","action":"APPROVE","confidence":1,"reasons":["rules allow"],"policy_refs":["payment-policy#2.1"]}\n\n',
      'id: pay_web_test:status\nevent: status\ndata: {"request_id":"pay_web_test","status":"APPROVED","decision_hash":"0xabc","keeperhub_execution_id":null,"transaction_hash":null}\n\n'
    ].join("");
    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream"
      },
      body: stream
    });
  });

  await page.goto("/payments/new");
  await expect(page.getByText("Analysis has not started yet")).toBeVisible();
  await page.getByRole("button", { name: /Submit demo payment/ }).click();
  await expect(page.getByText("Status: APPROVED")).toBeVisible();
  await expect(page.getByText("rules allow")).toBeVisible();
  await page.waitForTimeout(1500);
  expect(eventRequests).toBe(1);
});

test("audit guide explains demo ids versus real payment request ids", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Audit trail guide/ }).click();
  await expect(page.getByText("不是后端 PostgreSQL 里的真实付款请求 ID")).toBeVisible();
  await expect(page.getByText("/audit/pay_xxx")).toBeVisible();
});
