# Base Sepolia Setup Scripts

Use these scripts after `contracts/.env` has a valid `BASE_SEPOLIA_RPC_URL` and
`DEPLOYER_PRIVATE_KEY`.

## Deploy TreasuryGuard

```bash
npx hardhat run scripts/deploy.js --network baseSepolia
```

Copy the printed `treasuryGuard` address into:

- `contracts/.env` as `TREASURY_GUARD_ADDRESS`
- `apps/api/.env` as `TREASURY_GUARD_ADDRESS`

## Deploy MockUSDC

```bash
npm run deploy:mock-usdc:base-sepolia
```

Copy the printed `mockUSDC` address into:

- `contracts/.env` as `MOCK_USDC_ADDRESS`
- `apps/api/.env` as `DEMO_USDC_ADDRESS`

## Fund TreasuryGuard

```bash
npm run fund:guard:base-sepolia
```

This mints demo USDC directly to the deployed `TreasuryGuard` contract.

## Seed demo recipient whitelist

```bash
npm run seed:recipient:base-sepolia
```

By default this allows the local API demo vendor wallet
`0x1111111111111111111111111111111111111111`. To allow a real supplier wallet,
run:

```bash
npx hardhat run scripts/seed-recipient.js --network baseSepolia -- --recipient 0x...
```

## Grant KeeperHub executor role

Set `KEEPERHUB_WALLET_ADDRESS` in `apps/api/.env`, then run:

```bash
npm run grant:keeperhub:base-sepolia
```

`EXECUTOR_ROLE` is a `bytes32` role id defined inside `TreasuryGuard`, not an
address to paste into `.env`. The script reads it from the contract and grants
it to the KeeperHub EVM wallet.
