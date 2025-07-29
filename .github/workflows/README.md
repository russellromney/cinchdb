# GitHub Actions Workflows

## Deploy MkDocs to GitHub Pages (`deploy-docs.yml`)

This workflow automatically builds and deploys the MkDocs documentation to GitHub Pages.

### Triggers
- **Automatic**: On pushes to `main` branch when any of these files change:
  - Files in `docs/` directory
  - `mkdocs.yml` configuration
  - `requirements-docs.txt` dependencies
  - The workflow file itself
- **Manual**: Via GitHub Actions UI using `workflow_dispatch`

### Deployment Details
- **URL**: `https://<username>.github.io/cinchdb/`
- **Build Tool**: MkDocs with Material theme
- **Python Version**: 3.11
- **Caching**: Python pip dependencies are cached for faster builds

### How It Works
1. **Build Phase**:
   - Checks out the repository with full history
   - Sets up Python 3.11 with pip caching
   - Installs MkDocs and dependencies from `requirements-docs.txt`
   - Creates a modified `mkdocs.yml` with the correct GitHub Pages URL
   - Builds the static site to `./site` directory
   - Uploads the site as a GitHub Pages artifact

2. **Deploy Phase**:
   - Downloads the artifact from the build phase
   - Deploys to GitHub Pages

### Required Repository Settings
1. Go to **Settings** > **Pages**
2. Under **Source**, select **GitHub Actions**
3. The workflow will handle the rest automatically

### Permissions
The workflow requires these permissions (already configured):
- `contents: read` - To checkout the repository
- `pages: write` - To deploy to GitHub Pages
- `id-token: write` - For OIDC authentication with GitHub Pages

### Concurrency
- Only one deployment can run at a time
- New deployments wait for in-progress ones to complete
- This ensures production deployments aren't interrupted

### Rollback Strategy
If a deployment fails or introduces issues:
1. Revert the problematic commit in the `main` branch
2. The workflow will automatically redeploy the previous version
3. Or manually trigger a workflow run from a known good commit

### Local Testing
To test the documentation build locally:
```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Then visit `http://localhost:8000` in your browser.