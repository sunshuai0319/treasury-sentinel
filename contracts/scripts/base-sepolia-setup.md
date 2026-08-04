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

