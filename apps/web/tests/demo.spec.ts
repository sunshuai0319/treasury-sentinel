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

test("audit menu lists payments and opens a request's decision trail", async ({ page }) => {
  const review = {
    request_id: "pay_audit_menu",
    vendor_id: "vendor_demo",
    invoice_id: "inv_demo_over_limit",
    amount_units: 700000000,
    recipient_address: "0x1111111111111111111111111111111111111111",
    status: "REVIEW",
    final_action: "REVIEW",
    decision_hash: null,
    keeperhub_execution_id: null,
    transaction_hash: null,
    created_at: "2026-08-01T08:00:00"
  };
  await page.route("**/api/payment-requests", async (route) => {
    await route.fulfill({ json: [review] });
  });
  await page.route("**/api/payment-requests/pay_audit_menu/events**", async (route) => {
    const stream = [
      'id: run_menu:0\nevent: primary\ndata: {"actor":"primary","action":"REVIEW","confidence":0.72,"reasons":["amount exceeds auto-payment limit"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: run_menu:1\nevent: critic\ndata: {"actor":"critic","action":"REVIEW","confidence":0.78,"reasons":["critic requires finance approval"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: run_menu:2\nevent: final\ndata: {"actor":"final","action":"REVIEW","confidence":1,"reasons":["amount requires finance manager approval"],"policy_refs":["payment-policy#2.2"]}\n\n',
      'id: pay_audit_menu:status\nevent: status\ndata: {"request_id":"pay_audit_menu","status":"REVIEW","decision_hash":"0xdef","keeperhub_execution_id":null,"transaction_hash":null}\n\n'
    ].join("");
    await route.fulfill({
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
      body: stream
    });
  });

  await page.goto("/");
  await page.getByRole("link", { name: /Audit trail/ }).click();
  await expect(page.getByText("pay_audit_menu")).toBeVisible();
  await expect(page.getByText("700 USDC")).toBeVisible();
  await expect(page.getByText("2026-08-01 08:00")).toBeVisible();

  await page.getByRole("link", { name: /pay_audit_menu/ }).click();
  await expect(page.getByText("amount requires finance manager approval")).toBeVisible();
  await expect(page.locator(".step", { hasText: "primary" })).toBeVisible();
});

test("old demo-normal guide url redirects to the audit index", async ({ page }) => {
  await page.route("**/api/payment-requests", async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.goto("/audit/demo-normal");
  await expect(page).toHaveURL(/\/audit$/);
  await expect(page.getByText("No payment requests yet")).toBeVisible();
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
      transaction_hash: null,
      created_at: "2026-08-02T08:00:00"
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
      transaction_hash: null,
      created_at: "2026-08-03T08:00:00"
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
  await expect(page.getByText("2026-08-03 08:00")).toBeVisible();

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

test("payments lists real requests with status and links to detail and audit", async ({ page }) => {
  const approved = {
    request_id: "pay_hist_approved",
    vendor_id: "vendor_demo",
    invoice_id: "inv_demo_001",
    amount_units: 420000000,
    recipient_address: "0x1111111111111111111111111111111111111111",
    status: "APPROVED",
    final_action: "APPROVE",
    decision_hash: "0xabc",
    keeperhub_execution_id: null,
    transaction_hash: null,
    created_at: "2026-08-01T08:00:00"
  };
  const review = {
    request_id: "pay_hist_review",
    vendor_id: "vendor_demo",
    invoice_id: "inv_demo_over_limit",
    amount_units: 700000000,
    recipient_address: "0x1111111111111111111111111111111111111111",
    status: "REVIEW",
    final_action: "REVIEW",
    decision_hash: null,
    keeperhub_execution_id: null,
    transaction_hash: null,
    created_at: "2026-08-02T08:00:00"
  };
  const rejected = {
    request_id: "pay_hist_rejected",
    vendor_id: "vendor_demo",
    invoice_id: "inv_demo_mismatch",
    amount_units: 420000000,
    recipient_address: "0x2222222222222222222222222222222222222222",
    status: "REJECT",
    final_action: "REJECT",
    decision_hash: null,
    keeperhub_execution_id: null,
    transaction_hash: null,
    created_at: "2026-08-03T08:00:00"
  };
  await page.route("**/api/payment-requests", async (route) => {
    await route.fulfill({ json: [approved, review, rejected] });
  });
  await page.route("**/api/payment-requests/pay_hist_approved", async (route) => {
    await route.fulfill({ json: approved });
  });

  await page.goto("/payments");
  await expect(page.getByText("pay_hist_approved")).toBeVisible();
  await expect(page.getByText("pay_hist_review")).toBeVisible();
  await expect(page.getByText("pay_hist_rejected")).toBeVisible();
  // Status badges render the raw status text.
  await expect(page.getByText("APPROVED", { exact: true })).toBeVisible();
  await expect(page.getByText("REVIEW", { exact: true })).toBeVisible();
  await expect(page.getByText("REJECT", { exact: true })).toBeVisible();
  await expect(page.getByText("420 USDC").first()).toBeVisible();
  await expect(page.getByText("700 USDC")).toBeVisible();
  await expect(page.getByText("2026-08-01 08:00")).toBeVisible();

  await page.getByRole("link", { name: /pay_hist_approved/ }).click();
  await expect(page.getByText("APPROVED", { exact: true })).toBeVisible();
});

test("payments list paginates when there are more than five requests", async ({ page }) => {
  const all = Array.from({ length: 7 }, (_, i) => ({
    request_id: `pay_page_${i + 1}`,
    vendor_id: "vendor_demo",
    invoice_id: `inv_page_${i + 1}`,
    amount_units: 420000000 + i * 1000000,
    recipient_address: "0x1111111111111111111111111111111111111111",
    status: i % 2 === 0 ? "APPROVED" : "REVIEW",
    final_action: i % 2 === 0 ? "APPROVE" : "REVIEW",
    decision_hash: null,
    keeperhub_execution_id: null,
    transaction_hash: null,
    created_at: `2026-08-0${i + 1}T08:00:00`
  }));
  await page.route("**/api/payment-requests", async (route) => {
    await route.fulfill({ json: all });
  });

  await page.goto("/payments");
  await expect(page.getByText("pay_page_1")).toBeVisible();
  await expect(page.getByText("pay_page_5")).toBeVisible();
  await expect(page.getByText("pay_page_6")).not.toBeVisible();
  await expect(page.getByText("Page 1 of 2")).toBeVisible();

  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByText("pay_page_6")).toBeVisible();
  await expect(page.getByText("pay_page_7")).toBeVisible();
  await expect(page.getByText("pay_page_1")).not.toBeVisible();
  await expect(page.getByText("Page 2 of 2")).toBeVisible();

  await page.getByRole("button", { name: "Prev", exact: true }).click();
  await expect(page.getByText("pay_page_1")).toBeVisible();
  await expect(page.getByText("pay_page_6")).not.toBeVisible();
});

test("payments and audit lists link confirmed transactions to BaseScan", async ({ page }) => {
  const confirmed = {
    request_id: "pay_hist_confirmed",
    vendor_id: "vendor_demo",
    invoice_id: "inv_demo_001",
    amount_units: 420000000,
    recipient_address: "0x1111111111111111111111111111111111111111",
    status: "CONFIRMED",
    final_action: "APPROVE",
    decision_hash: "0xabc",
    keeperhub_execution_id: "exec_1",
    transaction_hash: "0x1234abcd5678ef",
    created_at: "2026-08-01T08:00:00"
  };
  const pending = {
    ...confirmed,
    request_id: "pay_hist_pending",
    invoice_id: "inv_demo_pending",
    status: "APPROVED",
    keeperhub_execution_id: null,
    transaction_hash: null
  };
  await page.route("**/api/payment-requests", async (route) => {
    await route.fulfill({ json: [confirmed, pending] });
  });
  const txHref = "https://sepolia.basescan.org/tx/0x1234abcd5678ef";

  await page.goto("/payments");
  const onChainLink = page.getByRole("link", { name: "BaseScan ↗" });
  await expect(onChainLink).toHaveCount(1);
  await expect(onChainLink).toHaveAttribute("href", txHref);
  await expect(onChainLink).toHaveAttribute("target", "_blank");
  // Only the confirmed row carries a tx link; the pending row shows a placeholder.
  await expect(page.getByLabel("No transaction yet")).toHaveCount(1);

  // Detail page surfaces the same on-chain link.
  await page.route("**/api/payment-requests/pay_hist_confirmed", async (route) => {
    await route.fulfill({ json: confirmed });
  });
  await page.getByRole("link", { name: /pay_hist_confirmed/ }).click();
  await expect(page.getByRole("link", { name: "View on BaseScan ↗" })).toHaveAttribute("href", txHref);

  // Audit index also exposes the on-chain link.
  await page.goto("/audit");
  await expect(page.getByRole("link", { name: "BaseScan ↗" })).toHaveCount(1);
});
