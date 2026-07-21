# Render service previews

This repository's preview service is deliberately independent of any production
service, database, disk, environment group, or secret. It is a Docker web
service that contains a small fictional fixture built into a root-owned,
mode-0444 DuckDB file. The runtime process is the unprivileged `vgc` user.

## Maintainer workflow

1. Review the author, CI result, and every Docker, Render, privacy, and data
   change. Never enable a preview for a fork, bot, or first-time contributor.
2. Add the `render-preview` label to a trusted pull request. Render's manual
   preview mode creates the temporary TLS URL; it updates on pushes and removes
   the instance when the pull request closes or merges.
3. Check `/api/health`, the synthetic-data label, and that `POST /api/refresh`
   returns `404`. Render adds `X-Robots-Tag: noindex` to preview responses.
4. Remove the label to tear the preview down early when it is no longer needed.

Do not add credentials, `sync: false` variables, environment groups, disks,
live data, `data/seed.json.gz`, or a generated local DuckDB file. Public and
noindex is not access control; follow the project preview-access policy before
sharing a URL.

## Local reviewer check

```bash
docker build -t vgc-analytics-preview .
docker run --rm -p 10000:10000 vgc-analytics-preview
curl -i http://127.0.0.1:10000/api/health
curl -i -X POST http://127.0.0.1:10000/api/refresh # must be 404
```

The image has no writable application data requirement. The reviewed local
health check used 62 MiB, well below Render Free's 512 MiB allowance. Recheck
with the command below while exercising the health and search endpoints if the
runtime dependencies or fixture grow.

```bash
docker stats --no-stream vgc-analytics-preview
```
