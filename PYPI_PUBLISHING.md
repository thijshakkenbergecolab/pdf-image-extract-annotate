# PyPI Publishing Setup Guide

This package uses GitHub Actions for automated PyPI publishing. There are two methods available:

## Method 1: API Token (Recommended for Quick Setup)

1. **Get a PyPI API Token:**
   - Log in to https://pypi.org
   - Go to Account Settings → API tokens
   - Create a new API token (scope: "Entire account" or specific to this project)
   - Copy the token (starts with `pypi-`)

2. **Add Token to GitHub Secrets:**
   - Go to your GitHub repository settings
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI token (including the `pypi-` prefix)
   - Click "Add secret"

3. **Trigger Publishing:**
   - Create a GitHub release, or
   - Manually trigger the workflow from Actions tab

## Method 2: Trusted Publishing with OIDC (More Secure, No Tokens)

1. **First, publish the package once using Method 1**
   - This creates the project on PyPI

2. **Configure Trusted Publisher on PyPI:**
   - Go to https://pypi.org and log in
   - Navigate to your project: https://pypi.org/manage/project/pdf-image-extract-annotate/
   - Go to "Settings" → "Publishing"
   - Add a new trusted publisher with these EXACT settings:
     - **Owner**: `thijshakkenbergecolab`
     - **Repository name**: `pdf-image-extract-annotate`
     - **Workflow name**: `publish.yml`
     - **Environment name**: (leave empty)

3. **Remove API Token (Optional):**
   - Once trusted publishing is configured, you can remove the `PYPI_API_TOKEN` secret
   - The workflow will automatically use OIDC authentication

## Current Workflow Status

The workflow is configured to:
- Try using the API token if `PYPI_API_TOKEN` secret exists
- Fall back to OIDC trusted publishing if no token is provided

## Troubleshooting

### "invalid-publisher" Error
This means PyPI received a valid OIDC token but couldn't find a matching trusted publisher configuration. Ensure:
- The repository owner matches exactly: `thijshakkenbergecolab`
- The repository name matches exactly: `pdf-image-extract-annotate`
- The workflow file is named: `publish.yml`
- No environment is specified in the trusted publisher configuration

### Claims Debug Information
When OIDC fails, the error message shows the claims being sent. These should match your PyPI trusted publisher configuration exactly:
- `repository`: `thijshakkenbergecolab/pdf-image-extract-annotate`
- `repository_owner`: `thijshakkenbergecolab`
- `workflow_ref`: Contains `.github/workflows/publish.yml`
- `environment`: Should be `MISSING` (no environment)

## Manual Publishing (Fallback)

If automated publishing fails, you can always publish manually:

```bash
# Build the package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

Enter `__token__` as username and your PyPI API token as password.