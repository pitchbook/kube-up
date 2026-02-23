# Contributing to Kube Up

Thank you for your interest in contributing to Kube Up! This document provides guidelines and instructions for contributing.

## Developer Certificate of Origin

This project requires all commits to be signed off with a Developer Certificate of Origin (DCO). By signing off your commits, you certify that you have the right to submit your contribution under the project's MIT license.

### What is the DCO?

The Developer Certificate of Origin is a lightweight way for contributors to certify that they wrote or otherwise have the right to submit the code they are contributing to the project. For more information, see [DCO](DCO).

### How to Sign Off

To sign off on your commits, add the `-s` or `--signoff` flag when committing:

```bash
git commit -s -m "Your commit message"
```

This automatically adds a "Signed-off-by" line to your commit message:

```
Your commit message

Signed-off-by: Your Name <your.email@example.com>
```

Git will use the name and email from your git configuration (`user.name` and `user.email`). To set these globally:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Signing Off Existing Commits

If you forgot to sign off commits in a local branch, you can amend them:

```bash
git commit --amend --no-edit -s
```

For multiple unsigned commits, you can use an interactive rebase:

```bash
git rebase -i HEAD~<number_of_commits> -x "git commit --amend --no-edit -s"
```

### DCO Verification

All pull requests are automatically checked to ensure commits are signed off. If your PR fails this check, simply sign off your commits as described above and push them again.

## Submitting Pull Requests

1. Create a feature branch:
   ```bash
   git checkout -b feat/description-of-change
   ```
2. Make your changes and sign off commits with `-s`
3. Push to your fork and submit a pull request
4. Ensure all checks pass:
   - DCO sign-off verification
   - Tests
   - Type checking
   - Linting

## Reporting Bugs

When reporting a bug, please include:

- A clear description of the issue
- Steps to reproduce the problem
- Expected behavior vs actual behavior
- Relevant logs or error messages
- Your environment (Kubernetes version, Helm version, etc.)

## Suggesting Enhancements

For feature requests:

- Provide a clear description of the proposed feature
- Explain the use case and motivation
- Describe how it would work
- Consider any potential impact on existing functionality

## Questions?

If you have questions about contributing, please:

- Check existing [GitHub Issues](https://github.com/pitchbook/kube-up/issues)
- Check the [documentation](./documentation/)
- Open a new issue with your question

Thank you for contributing to Kube Up!
