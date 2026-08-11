# Treasury Sentinel Demo Script

This file is generated from the deterministic local demo runner.

## Base Sepolia contracts

- TreasuryGuard: `0xE4F52719FC5696e5d746e25E9224518e13f0CEf9`
- MockUSDC: `0x8eEf98476B371BF01D99CBCEA4D7745B49040c95`
- Chain ID: `84532`

## Scenario order

1. `normal` → `APPROVE`
   - Request: `demo-normal`
   - Invoice: `INV-2026-DEMO`
   - Final reasons: approved vendor, matching wallet, unpaid invoice, amount <= 500 USDC (供应商已批准、钱包匹配、发票未支付、金额≤500 USDC)
   - Policy refs: 2.1 自动付款
2. `duplicate` → `REJECT`
   - Request: `demo-duplicate`
   - Invoice: `INV-2026-DEMO`
   - Final reasons: duplicate invoice or content hash (重复发票或内容哈希)
   - Policy refs: 1.1 重复发票
3. `address_mismatch` → `REJECT`
   - Request: `demo-address_mismatch`
   - Invoice: `INV-2026-DEMO`
   - Final reasons: recipient address does not match vendor wallet (收款地址与供应商钱包不匹配)
   - Policy refs: 2.1 自动付款
4. `over_limit` → `REVIEW`
   - Request: `demo-over_limit`
   - Invoice: `INV-2026-DEMO`
   - Final reasons: amount requires finance manager approval (金额需财务经理审批)
   - Policy refs: 2.2 单级审批
5. `pause` → `PAUSE`
   - Request: `demo-pause`
   - Invoice: `INV-2026-DEMO`
   - Final reasons: address anomaly threshold reached
   - Policy refs: 1.1 地址异常

## Local API workflow assertions

- `normal` request `pay_cfce084a59fb` → `APPROVE`
- `address_mismatch` request `pay_26006cdc7d79` → `REJECT`
- `over_limit` request `pay_67827d42cdfd` → `REVIEW`

## KeeperHub / transaction evidence

Live KeeperHub execution is intentionally blocked until `KEEPERHUB_API_KEY` and `KEEPERHUB_WALLET_ADDRESS` are configured. Do not replace this section with mock tx hashes.
