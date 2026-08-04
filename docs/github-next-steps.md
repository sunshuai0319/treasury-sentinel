# GitHub Next Steps

Current branch:

```bash
git branch --show-current
```

Push the feature branch:

```bash
git push -u origin feature/treasury-sentinel-mvp
```

If GitHub has no default branch yet, create the remote branch from this work and
open a PR into `main`. If the remote `main` already exists later, fetch first:

```bash
git fetch origin
git status --short --branch
```

Recommended release flow:

```bash
git checkout main
git merge --ff-only feature/treasury-sentinel-mvp
git push origin main
```

For hackathon submission, include:

- Repository URL
- `docs/treasury-sentinel-project-plan.md`
- `docs/onboarding-quickstart.md`
- Base Sepolia contract address
- KeeperHub execution id
- Transaction hash
- Demo video

