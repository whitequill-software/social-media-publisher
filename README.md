# Social Media Publisher

A GitHub Actions-ready Python pipeline that runs daily at **9:00 a.m. Asia/Taipei**, selects a random image from a Google Drive folder, asks Gemini to create a condo sales caption using [`erin.md`](erin.md), and publishes the image and caption to a Facebook Page and Instagram professional account.

The CLI is safe by default: `social-publisher` creates a preview and **does not publish** unless `--publish` is supplied.

## How it works

1. Google Drive API lists image files in one configured folder and selects one using a secure random choice.
2. The selected image is downloaded for Gemini image understanding.
3. Gemini combines the image with Erin's rules and business context in `erin.md`.
4. In publish mode, the image bytes are uploaded directly to Facebook.
5. The pipeline uses Facebook's resulting CDN image URL to create, wait for, and publish an Instagram media container.

The Google Drive folder can remain private. The Google account that grants OAuth access only needs to be able to read it; Instagram receives the image from Facebook's CDN after the Facebook upload.

## Requirements

- Python 3.11+
- A Google Cloud project with Drive API enabled and an OAuth 2.0 Desktop app client
- A Gemini API key
- A Facebook Page and linked Instagram **professional** account
- A Meta app/access token with the permissions required for Page and Instagram content publishing

## Local setup

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Fill in `.env` with the Drive OAuth client ID, client secret, and refresh token. `.env` and downloaded OAuth client-secret files are git-ignored. Edit `erin.md` with real, approved property and brand details.

Run a non-publishing preview:

```powershell
social-publisher --seed 1
```

Review the printed image and caption. Only when ready, publish both platforms:

```powershell
social-publisher --publish
```

To publish only to Facebook while Instagram is not configured:

```powershell
social-publisher --publish --facebook-only
```

## Google Drive setup

1. Enable Google Drive API, configure the OAuth consent screen, and create an OAuth 2.0 **Desktop app** client in Google Cloud.
2. Download the client JSON as `client_secret.json` in the project folder. It is git-ignored and must never be committed.
3. Run `python get_refresh_token.py` once on a computer with a browser, sign in as the Google account that owns or can read the image folder, and approve read-only Drive access.
4. Copy the printed `GDRIVE_CLIENT_ID`, `GDRIVE_CLIENT_SECRET`, and `GDRIVE_REFRESH_TOKEN` values into `.env`. The production workflow uses the same values as GitHub Secrets and refreshes the short-lived access token without a browser.
5. Copy the folder ID from `https://drive.google.com/drive/folders/FOLDER_ID`. The folder does not need public link sharing.

The refresh token is tied to the scopes granted during consent. If you previously generated it with a different scope, run `get_refresh_token.py` again and save the new refresh token.

Images may be JPEG, PNG, or another format accepted by the current Meta publishing API. Use JPEG for the most predictable Facebook/Instagram compatibility.

## Meta setup

Connect the Instagram professional account to the Facebook Page. Create a Meta app and obtain a Page-capable access token with the current content-publishing permissions required by your app type and account. Set the Page ID, Instagram account ID, access token, and current Graph API version in the environment.

Meta access tokens expire or can be revoked. Use a long-lived supported token flow and rotate the GitHub secret before expiration. The workflow intentionally fails loudly when a platform rejects a request; because Facebook is posted before Instagram, a later Instagram failure can leave a Facebook-only post that needs manual review.

## GitHub Actions setup (after local review)

Create an empty GitHub repository later, add it as the remote, then configure these Actions secrets:

- `GOOGLE_DRIVE_FOLDER_ID`
- `GDRIVE_CLIENT_ID`
- `GDRIVE_CLIENT_SECRET`
- `GDRIVE_REFRESH_TOKEN`
- `GEMINI_API_KEY`
- `META_ACCESS_TOKEN`
- `FACEBOOK_PAGE_ID`
- `INSTAGRAM_ACCOUNT_ID`

Optional repository variables are `GEMINI_MODEL` and `META_GRAPH_API_VERSION`. The scheduled workflow uses `0 1 * * *` because GitHub cron is UTC and Taiwan is UTC+8 without daylight-saving changes. Scheduled executions publish to Facebook and Instagram; manual executions default to dry-run and require an explicit `publish` checkbox.

GitHub schedules can start later than the exact minute during high load. Keep the workflow enabled and ensure Actions are allowed in repository settings.

## Development

```powershell
ruff check .
pytest --cov=social_media_publisher
```

No API credentials are needed for the unit tests; all external services are faked.

## Operational notes

- Selection is random and does not prevent repeats. Remove or move used images if every image must be posted only once.
- There is no cross-platform transaction: one platform can succeed while the other fails.
- Never commit `.env`, OAuth client-secret files, refresh tokens, or Meta tokens.
- The pipeline exits non-zero on missing configuration, an empty Drive folder, a private/non-image public URL, an empty Gemini response, or a Meta error.

## References

- [Google Drive: search for files](https://developers.google.com/workspace/drive/api/guides/search-files)
- [Google Drive: download files](https://developers.google.com/workspace/drive/api/guides/manage-downloads)
- [Gemini text and multimodal generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [Instagram content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Facebook Page photos endpoint](https://developers.facebook.com/docs/graph-api/reference/page/photos/)

## License

MIT — see [`LICENSE`](LICENSE).
