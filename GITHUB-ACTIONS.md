# GitHub Actions - Docker Image Publishing

This document explains the automated Docker image build and publish workflow.

## Overview

The GitHub Actions workflow automatically builds and publishes Docker images to GitHub Container Registry (GHCR) whenever changes are pushed to the main branch or when version tags are created.

## Workflow Details

### File Location
`.github/workflows/docker-publish.yml`

### Triggers

The workflow runs on:
1. **Push to main branch** - Automatically builds and pushes with `latest` tag
2. **Version tags** (e.g., `v1.0.0`) - Builds and pushes with version tags
3. **Pull requests to main** - Builds only (doesn't push) for testing

### What It Does

1. **Checks out the code**
2. **Sets up Docker Buildx** for advanced build features
3. **Logs into GitHub Container Registry** using automatic token
4. **Extracts metadata** for tagging:
   - `latest` - for main branch
   - Version tags - for releases
   - SHA tags - for specific commits
5. **Builds the Docker image** from the Dockerfile
6. **Pushes to GHCR** at `ghcr.io/pinhead001/notetime`
7. **Creates attestation** for supply chain security

### Tags Generated

| Trigger | Tags Created |
|---------|-------------|
| Push to main | `latest`, `main-<sha>` |
| Tag `v1.0.0` | `1.0.0`, `1.0`, `1`, `latest` |
| Tag `v2.1.3` | `2.1.3`, `2.1`, `2`, `latest` |
| Pull Request | (build only, no push) |

## Using the Published Images

### Pull the Latest Image

```bash
docker pull ghcr.io/pinhead001/notetime:latest
```

### Pull a Specific Version

```bash
docker pull ghcr.io/pinhead001/notetime:1.0.0
```

### Run the Published Image

```bash
docker run -d \
  --name notetime \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  ghcr.io/pinhead001/notetime:latest
```

### Use in Docker Compose

Edit `docker-compose.yml` to use the published image instead of building locally:

```yaml
services:
  web:
    image: ghcr.io/pinhead001/notetime:latest
    # Remove the 'build: .' line
    container_name: notetime-app
    environment:
      DATABASE_URL: postgresql://notetime:notetime@db:5432/notetime
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
```

Then run:
```bash
docker-compose pull  # Pull latest image
docker-compose up -d
```

## Creating a New Release

### Step 1: Update VERSION File

```bash
# Edit VERSION file
echo "1.1.0" > VERSION
git add VERSION
git commit -m "Bump version to 1.1.0"
git push origin main
```

### Step 2: Create a Git Tag

```bash
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0
```

### Step 3: Wait for GitHub Actions

- Go to: https://github.com/pinhead001/notetime/actions
- Watch the workflow run
- When complete, image will be available at: `ghcr.io/pinhead001/notetime:1.1.0`

### Step 4: Verify the Image

```bash
docker pull ghcr.io/pinhead001/notetime:1.1.0
docker images | grep notetime
```

## Viewing Published Images

### On GitHub

1. Go to: https://github.com/pinhead001/notetime
2. Click "Packages" on the right sidebar
3. Click on "notetime" package
4. View all published versions and tags

### From Command Line

```bash
# List available tags (requires GitHub CLI)
gh api /users/pinhead001/packages/container/notetime/versions
```

## Making Images Public

By default, GHCR images are private. To make them public:

1. Go to: https://github.com/users/pinhead001/packages/container/notetime/settings
2. Scroll to "Danger Zone"
3. Click "Change visibility"
4. Select "Public"
5. Confirm

Now anyone can pull without authentication:
```bash
docker pull ghcr.io/pinhead001/notetime:latest
```

## Workflow Permissions

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions.

Required permissions (already configured):
- `contents: read` - Read repository code
- `packages: write` - Push to GitHub Container Registry

## Caching

The workflow uses GitHub Actions cache to speed up builds:
- Docker layer caching
- Subsequent builds are much faster (30s vs 3-5 minutes)

## Troubleshooting

### Workflow Fails to Push

**Check permissions:**
1. Go to repository Settings
2. Actions → General
3. Workflow permissions → Select "Read and write permissions"
4. Save

### Can't Pull Image

**If image is private, authenticate first:**

```bash
# Create a personal access token with 'read:packages' scope
# Then login:
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Now pull:
docker pull ghcr.io/pinhead001/notetime:latest
```

### Build Fails

**Check workflow logs:**
1. Go to: https://github.com/pinhead001/notetime/actions
2. Click on the failed workflow run
3. Click on "build-and-push" job
4. Review error messages

**Common issues:**
- Dockerfile syntax errors
- Missing files (check .dockerignore)
- Build context too large

### Wrong Tags

**Check metadata configuration** in `.github/workflows/docker-publish.yml`:
```yaml
tags: |
  type=ref,event=branch
  type=semver,pattern={{version}}
  type=raw,value=latest,enable={{is_default_branch}}
```

## Advanced Usage

### Building for Multiple Platforms

Add to workflow:
```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    platforms: linux/amd64,linux/arm64
    push: ${{ github.event_name != 'pull_request' }}
    tags: ${{ steps.meta.outputs.tags }}
```

### Custom Build Arguments

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    build-args: |
      VERSION=${{ github.ref_name }}
      BUILD_DATE=${{ github.event.head_commit.timestamp }}
    push: ${{ github.event_name != 'pull_request' }}
    tags: ${{ steps.meta.outputs.tags }}
```

### Scanning for Vulnerabilities

Add after build step:
```yaml
- name: Scan image for vulnerabilities
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload Trivy results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

## Production Deployment

### Pull and Run Latest Image

```bash
# On production server
docker pull ghcr.io/pinhead001/notetime:latest
docker stop notetime || true
docker rm notetime || true
docker run -d \
  --name notetime \
  --restart unless-stopped \
  -p 8000:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  -e ENVIRONMENT="production" \
  ghcr.io/pinhead001/notetime:latest
```

### With Docker Compose

```yaml
services:
  web:
    image: ghcr.io/pinhead001/notetime:1.0.0  # Pin to specific version
    restart: unless-stopped
    environment:
      DATABASE_URL: ${DATABASE_URL}
      ENVIRONMENT: production
    ports:
      - "8000:8000"
```

Deploy:
```bash
docker-compose pull
docker-compose up -d
```

### Update to New Version

```bash
# Pull new version
docker pull ghcr.io/pinhead001/notetime:1.1.0

# Update docker-compose.yml to new version
sed -i 's/notetime:1.0.0/notetime:1.1.0/' docker-compose.yml

# Restart with new version
docker-compose up -d
```

## Monitoring Builds

### GitHub Actions Badge

Add to README.md:
```markdown
![Docker Build](https://github.com/pinhead001/notetime/actions/workflows/docker-publish.yml/badge.svg)
```

### Notifications

Configure in: Repository Settings → Notifications
- Email on workflow failure
- Slack/Discord webhooks

## Security Best Practices

1. **Pin versions in production** - Don't use `latest` in production
2. **Scan images** - Use Trivy or similar tools
3. **Keep base images updated** - Rebuild regularly for security patches
4. **Use minimal base images** - We use `python:3.12-slim`
5. **Review dependencies** - Check requirements.txt regularly
6. **Enable attestations** - Already configured in workflow

## Related Documentation

- [Docker Setup](DOCKER.md)
- [Docker for Windows](DOCKER-WINDOWS.md)
- [Git Instructions](GIT-instructions.md)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [GHCR Docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## Quick Reference

```bash
# Pull latest
docker pull ghcr.io/pinhead001/notetime:latest

# Pull specific version
docker pull ghcr.io/pinhead001/notetime:1.0.0

# Run container
docker run -d -p 8000:8000 ghcr.io/pinhead001/notetime:latest

# View workflow runs
# https://github.com/pinhead001/notetime/actions

# View packages
# https://github.com/pinhead001/notetime/pkgs/container/notetime

# Create release
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

## Summary

- ✅ Automated builds on push to main
- ✅ Version tagging with semantic versioning
- ✅ Published to GitHub Container Registry
- ✅ Caching for faster builds
- ✅ Supply chain attestation
- ✅ Easy to pull and deploy
- ✅ Production-ready workflow
