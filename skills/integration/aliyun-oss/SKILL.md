---
name: aliyun-oss
description: "Upload, list, share, and delete files on Aliyun OSS. Returns public or pre-signed URLs so you can hand artefacts to users (DingTalk / WeChat / web) without leaving local files behind. Credentials live in the Hermes vault — the LLM never sees AK/SK plaintext."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [aliyun, oss, upload, share, integration]
    related_skills: [canvas]
---

# Aliyun OSS skill

A thin wrapper around `oss2` (Aliyun's official Python SDK) that uploads files to OSS and returns a URL. Use this whenever you need to **hand a deliverable (image, PDF, archive) to a user** — especially over channels (DingTalk, WeChat, Feishu, browser previews) where local file paths don't work.

## When to use

- You produced an artefact (e.g. a PNG from `canvas`, a PDF, a zip) and need a URL the user can open or share
- The user asks "give me a link" / "can I download it" / "send to DingTalk"
- The conversation runs in a remote / containerised environment where local paths are useless to the user

## When NOT to use

- The user explicitly asked for a local file path on their own machine
- The artefact is sensitive and must not leave the host
- A `dashscope` / `dingtalk` / `feishu` channel-native upload API exists for that file type — prefer those when available (they handle expiry & ACL)

## Configuration via Hermes vault

Credentials are read from the **Hermes vault** (`~/.hermes/vault.yaml`). The skill never reads them from environment variables or shell prompts. To configure:

```bash
hermes vault add OSS_DEFAULT_ENDPOINT --value oss-cn-hangzhou.aliyuncs.com
hermes vault add OSS_DEFAULT_BUCKET   --value my-bucket
hermes vault add OSS_DEFAULT_AK       --value LTAI5t...
hermes vault add OSS_DEFAULT_SK       --value xxxxxxxx
# Optional:
hermes vault add OSS_DEFAULT_PREFIX   --value hermes/        # all uploads go under this prefix
hermes vault add OSS_DEFAULT_PUBLIC   --value true           # default to public-read URLs (no signature)
```

Each profile uses 5 vault keys: `OSS_<PROFILE>_{ENDPOINT,BUCKET,AK,SK,PREFIX}` (PREFIX & PUBLIC optional). You can keep multiple profiles side-by-side, e.g. `OSS_DEV_*` and `OSS_PROD_*`, then pass `--profile dev`.

The skill subprocess reads `vault.yaml` directly (file is 0600 inside the same user's HOME), so credentials never round-trip through the LLM context.

## Commands

All commands are dispatched through `scripts/oss_cli.py`:

```bash
python scripts/oss_cli.py info     [--profile NAME]
python scripts/oss_cli.py upload   <local_path> [--key OSS_KEY] [--profile NAME] [--public] [--expires SECONDS]
python scripts/oss_cli.py share    <oss_key>    [--profile NAME] [--expires SECONDS]
python scripts/oss_cli.py list     [--prefix PREFIX] [--profile NAME] [--limit N]
python scripts/oss_cli.py delete   <oss_key>    [--profile NAME]
```

### upload

```
python scripts/oss_cli.py upload ~/.hermes/canvas.png --profile default
```

- `<local_path>` — file on disk to upload
- `--key OSS_KEY` — object key inside the bucket; default is `<prefix>/<yyyy-mm-dd>/<uuid>-<basename>`
- `--public` — emit the un-signed `https://bucket.endpoint/key` URL (requires bucket ACL `public-read` or per-object ACL set)
- `--expires SECONDS` — return a pre-signed URL valid for N seconds (default 86400)

Returns a JSON line on stdout:

```json
{"ok": true, "url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/...", "key": "hermes/2026-05-26/...png", "size": 81133, "etag": "...", "expires_in": 86400, "profile": "default", "public": false}
```

### share

Generate a fresh pre-signed URL for an existing object (e.g. re-share after expiry):

```
python scripts/oss_cli.py share hermes/2026-05-26/abcd.png --expires 604800
```

### list

```
python scripts/oss_cli.py list --prefix hermes/2026-05-26/ --limit 20
```

### info

Prints the active profile's endpoint / bucket / prefix (no AK/SK). Useful to confirm you're talking to the right bucket before uploading.

### delete

Removes an object. Idempotent; succeeds on missing keys.

## Vault placeholder mode (LLM tool-call surface)

When invoked **as a Hermes tool** (vs. directly via shell), the LLM passes only `--profile`, `--key`, etc. — never the AK/SK. The placeholder engine never resolves OSS_*_SK to plaintext in tool-call args because the skill subprocess reads the vault file by itself.

If you absolutely need to call the CLI from a non-Hermes shell (e.g. local debugging) without going through the vault, set:

```
OSS_<PROFILE>_AK=...  OSS_<PROFILE>_SK=...  OSS_<PROFILE>_ENDPOINT=...  OSS_<PROFILE>_BUCKET=...  python scripts/oss_cli.py upload ...
```

Env vars take precedence over the vault for that key — useful in CI but **never** the path the agent uses.

## Output contract (for the agent)

The CLI always emits **one JSON line per command** to stdout. Errors include `{"ok": false, "error": "..."}` and exit non-zero. The agent should:

1. Run the command
2. `JSON.parse` stdout's last line
3. On `ok: true`, present `url` to the user (in chat / IM / wherever)
4. On `ok: false`, surface `error` to the user with the next-step hint

Do **not** parse or reformat AK/SK from any error message — they should never appear there, but if they do (SDK bug), redact before forwarding.

## Setup (one-time)

```bash
cd "$HERMES_HOME/skills/integration/aliyun-oss"
pip install -r requirements.txt   # oss2, pyyaml
# Configure credentials:
hermes vault add OSS_DEFAULT_ENDPOINT
hermes vault add OSS_DEFAULT_BUCKET
hermes vault add OSS_DEFAULT_AK
hermes vault add OSS_DEFAULT_SK
# Sanity check:
python scripts/oss_cli.py info
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `vault entries not found: OSS_DEFAULT_*` | Run `hermes vault list` to confirm names exist; re-add with `hermes vault add OSS_<PROFILE>_<KEY>`. |
| `oss2 not installed` | `pip install -r requirements.txt` inside this skill folder. |
| `403 SignatureDoesNotMatch` | AK/SK wrong, or system clock drift > 15min. Check `date -u`. |
| `403 AccessDenied` on `--public` URL | The bucket / object ACL is private. Either set `bucket.acl=public-read` (Aliyun console) or drop `--public` to use a pre-signed URL. |
| URL works in browser but not in DingTalk | DingTalk requires `https://` and ContentType image/*. Ensure object's MIME was inferred correctly (the CLI sets it from extension). |

## Related skills

- `creative/canvas` — produces PNG; pipe its output here when the user wants a URL
- `productivity/google-workspace` — same vault-based credential pattern (good reference)
