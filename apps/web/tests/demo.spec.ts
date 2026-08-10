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
  let createdPayload: { amount_units: number } | undefined;
  await page.route("**/api/payment-requests", async (route) => {
    createdPayload = route.request().postDataJSON() as { amount_units: number };
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
  await page.getByRole("button", { name: /Submit Normal auto payment/ }).click();
  await expect(page.getByText("Status: APPROVED")).toBeVisible();
  await expect(page.getByText("rules allow")).toBeVisible();
  await page.waitForTimeout(1500);
  expect(createdPayload?.amount_units).toBe(420000000);
  expect(eventRequests).toBe(1);
});

test("resubmitting a payment does not render the previous run's timeline", async ({ page }) => {
  let createdCount = 0;
  await page.route("**/api/payment-requests", async (route) => {
    createdCount += 1;
    const id = createdCount === 1 ? "pay_first_web_test" : "pay_second_web_test";
    await route.fulfill({
      json: {
        request_id: id,
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
  const analyze = async (route: { fulfill: (arg0: { status: number; json: object }) => Promise<void> }, id: string) => {
    await route.fulfill({
      status: 202,
      json: {
        request_id: id,
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
  };
  await page.route("**/api/payment-requests/pay_first_web_test/analyze", async (route) => analyze(route, "pay_first_web_test"));
  await page.route("**/api/payment-requests/pay_second_web_test/analyze", async (route) => analyze(route, "pay_second_web_test"));
  await page.route("**/api/payment-requests/pay_first_web_test/events**", async (route) => {
    const stream = [
      'id: run_first:0\nevent: primary\ndata: {"actor":"primary","action":"APPROVE","confidence":0.72,"reasons":["primary checked policy"],"policy_refs":["payment-policy#2.1"]}\n\n',
      'id: run_first:1\nevent: critic\ndata: {"actor":"critic","action":"APPROVE","confidence":0.78,"reasons":["critic agrees"],"policy_refs":["payment-policy#2.1"]}\n\n',
      'id: run_first:2\nevent: final\ndata: {"actor":"final","action":"APPROVE","confidence":1,"reasons":["rules allow"],"policy_refs":["payment-policy#2.1"]}\n\n',
      'id: pay_first_web_test:status\nevent: status\ndata: {"request_id":"pay_first_web_test","status":"APPROVED","decision_hash":"0xabc","keeperhub_execution_id":null,"transaction_hash":null}\n\n'
    ].join("");
    await route.fulfill({
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
      body: stream
    });
  });
  // Second request's event stream stays open without events: the previous
  // run's timeline must not leak into it while nothing has streamed yet.
  await page.route("**/api/payment-requests/pay_second_web_test/events**", async () => {
    // Intentionally never fulfill — the stream is open but silent.
  });

  await page.goto("/payments/new");
  await page.getByRole("button", { name: /Submit Normal auto payment/ }).click();
  await expect(page.getByText("Status: APPROVED")).toBeVisible();
  await expect(page.getByText("rules allow")).toBeVisible();

  // Same preset again — creates a second, identical payment request.
  await page.getByRole("button", { name: /Submit Normal auto payment/ }).click();
  await expect(page.getByText(/pay_second_web_test/)).toBeVisible();
  await expect(page.getByText("rules allow")).not.toBeVisible();
  await expect(page.getByText("Analysis has not started yet")).toBeVisible();
});

test("new payment preset can demonstrate over-limit review path", async ({ page }) => {
  let createdPayload: { amount_units: number; invoice_id: string } | undefined;
  await page.route("**/api/payment-requests", async (route) => {
    createdPayload = route.request().postDataJSON() as { amount_units: number; invoice_id: string };
    await route.fulfill({
      json: {
        request_id: "pay_over_limit_web_test",
        vendor_id: "vendor_demo",
        invoice_id: "inv_demo_over_limit",
        amount_units: 700000000,
        recipient_address: "0x1111111111111111111111111111111111111111",
        status: "SUBMITTED",
        final_action: null,
        decision_hash: null,
        keeperhub_execution_id: null,
        transaction_hash: null
      }
    });
  });
  await page.route("**/api/payment-requests/pay_over_limit_web_test/analyze", async (route) => {
    await route.fulfill({
      status: 202,
      json: {
        request_id: "pay_over_limit_web_test",
        invoice_id: "inv_demo_over_limit",
        vendor_id: "vendor_demo",
        amount_units: 700000000,
        recipient_address: "0x1111111111111111111111111111111111111111",
        status: "ANALYZING",
        final_action: null,
        decision_hash: null,
        keeperhub_execution_id: null,
        transaction_hash: null
      }
    });
  });
  await page.route("**/api/payment-requests/pay_over_limit_web_test/events**", async (route) => {
    const stream = [
      'id: run_over_limit_web_test:0\nevent: primary\ndata: {"actor":"primary","action":"REVIEW","confidence":0.72,"reasons":["amount exceeds auto-payment limit"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: run_over_limit_web_test:1\nevent: critic\ndata: {"actor":"critic","action":"REVIEW","confidence":0.78,"reasons":["critic requires finance approval"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: run_over_limit_web_test:2\nevent: final\ndata: {"actor":"final","action":"REVIEW","confidence":1,"reasons":["amount requires finance manager approval"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: pay_over_limit_web_test:status\nevent: status\ndata: {"request_id":"pay_over_limit_web_test","status":"REVIEW","decision_hash":"0xdef","keeperhub_execution_id":null,"transaction_hash":null}\n\n'
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
  await page.getByRole("button", { name: /Over 500 USDC/ }).click();
  await expect(page.getByText("700000000")).toBeVisible();
  await page.getByRole("button", { name: /Submit Over 500 USDC/ }).click();
  await expect(page.getByText("Status: REVIEW")).toBeVisible();
  await expect(page.getByText("amount requires finance manager approval")).toBeVisible();
  expect(createdPayload).toMatchObject({ amount_units: 700000000, invoice_id: "inv_demo_over_limit" });
});

test("audit guide explains demo ids versus real payment request ids", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Audit trail guide/ }).click();
  await expect(page.getByText("不是后端 PostgreSQL 里的真实付款请求 ID")).toBeVisible();
  await expect(page.getByText("/audit/pay_xxx")).toBeVisible();
});


test("approvals lists review payments and approves or rejects them", async ({ page }) => {
  let reviews = [
    {
      request_id: "pay_review_1",
      vendor_id: "vendor_demo",
      invoice_id: "inv_demo_over_limit",
      amount_units: 700000000,
      recipient_address: "0x1111111111111111111111111111111111111111",
      status: "REVIEW",
      final_action: "REVIEW",
      decision_hash: null,
      keeperhub_execution_id: null,
      transaction_hash: null
    },
    {
      request_id: "pay_review_2",
      vendor_id: "vendor_demo",
      invoice_id: "inv_demo_over_limit_2",
      amount_units: 900000000,
      recipient_address: "0x1111111111111111111111111111111111111111",
      status: "REVIEW",
      final_action: "REVIEW",
      decision_hash: null,
      keeperhub_execution_id: null,
      transaction_hash: null
    }
  ];
  await page.route("**/api/payment-requests?status=REVIEW", async (route) => {
    await route.fulfill({ json: reviews });
  });
  await page.route("**/api/payment-requests/pay_review_1/approve", async (route) => {
    reviews = reviews.filter((item) => item.request_id !== "pay_review_1");
    await route.fulfill({
      json: {
        ...reviews[0],
        status: "APPROVED",
        final_action: "APPROVE"
      }
    });
  });
  await page.route("**/api/payment-requests/pay_review_2/reject", async (route) => {
    reviews = reviews.filter((item) => item.request_id !== "pay_review_2");
    await route.fulfill({
      json: {
        request_id: "pay_review_2",
        vendor_id: "vendor_demo",
        invoice_id: "inv_demo_over_limit_2",
        amount_units: 900000000,
        recipient_address: "0x1111111111111111111111111111111111111111",
        status: "REJECT",
        final_action: "REJECT",
        decision_hash: null,
        keeperhub_execution_id: null,
        transaction_hash: null
      }
    });
  });

  await page.goto("/approvals");
  await expect(page.getByText("pay_review_1")).toBeVisible();
  await expect(page.getByText("pay_review_2")).toBeVisible();
  await expect(page.getByText("700 USDC")).toBeVisible();

  await page.getByRole("button", { name: /Approve/ }).first().click();
  await expect(page.getByText("pay_review_1")).not.toBeVisible();
  await expect(page.getByText("pay_review_2")).toBeVisible();

  await page.getByRole("button", { name: /Reject/ }).click();
  await expect(page.getByText("No payments awaiting review.")).toBeVisible();
});

test("audit page streams the real decision trail for a payment id", async ({ page }) => {
  await page.route("**/api/payment-requests/pay_audit_web_test/events**", async (route) => {
    const stream = [
      'id: run_audit:0\nevent: primary\ndata: {"actor":"primary","action":"REVIEW","confidence":0.72,"reasons":["amount exceeds auto-payment limit"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: run_audit:1\nevent: critic\ndata: {"actor":"critic","action":"REVIEW","confidence":0.78,"reasons":["critic requires finance approval"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: run_audit:2\nevent: final\ndata: {"actor":"final","action":"REVIEW","confidence":1,"reasons":["amount requires finance manager approval"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: pay_audit_web_test:status\nevent: status\ndata: {"request_id":"pay_audit_web_test","status":"REVIEW","decision_hash":"0xdef","keeperhub_execution_id":null,"transaction_hash":null}\n\n'
    ].join("");
    await route.fulfill({
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
      body: stream
    });
  });

  await page.goto("/audit/pay_audit_web_test");
  await expect(page.getByText("amount requires finance manager approval")).toBeVisible();
  // Actor names also appear in the intro copy, so scope to the timeline rows.
  await expect(page.locator(".step", { hasText: "primary" })).toBeVisible();
  await expect(page.locator(".step", { hasText: "critic" })).toBeVisible();
  await expect(page.locator(".step", { hasText: "final" })).toBeVisible();
});
