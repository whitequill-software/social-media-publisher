# Google Drive without manually managed refresh tokens

Use GitHub Actions OIDC -> Google Workload Identity Federation -> a service account.
Each run obtains short-lived credentials automatically. No downloaded service account key,
Google OAuth client secret, or Google refresh token is needed for this mode.
Tokens still expire; the runtime handles obtaining them.

## One-time setup for this repository

Run these commands in Google Cloud Shell while signed in to an account allowed to enable
APIs, create service accounts and identity pools, and change service account IAM policies.
They target project `social-media-publisher`. No billable compute is provisioned.
If these resource names already exist, inspect and reuse them rather than recreating them.

```bash
PROJECT_ID="social-media-publisher"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SA_EMAIL="social-publisher@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud services enable drive.googleapis.com iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com --project="$PROJECT_ID"

gcloud iam service-accounts create social-publisher --project="$PROJECT_ID" --display-name="Social publisher Drive reader"

gcloud iam workload-identity-pools create github-social-publisher --project="$PROJECT_ID" --location=global --display-name="Social publisher GitHub"

gcloud iam workload-identity-pools providers create-oidc github \
  --project="$PROJECT_ID" --location=global \
  --workload-identity-pool=github-social-publisher \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id" \
  --attribute-condition="assertion.repository_owner_id == '245847451' && assertion.repository_id == '1308221608' && assertion.ref == 'refs/heads/main' && assertion.workflow_ref == 'whitequill-software/social-media-publisher/.github/workflows/publish.yml@refs/heads/main' && assertion.event_name in ['schedule', 'workflow_dispatch']"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$PROJECT_ID" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-social-publisher/attribute.repository_id/1308221608"

echo "GCP_SERVICE_ACCOUNT=$SA_EMAIL"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER=projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-social-publisher/providers/github"
```

The condition restricts access to this repository's publishing workflow on `main`, for
scheduled or manual runs. Pull requests and other repositories cannot use this provider.
IAM changes can take several minutes to propagate. No project-wide Editor/Owner role or
domain-wide delegation is needed for the service account.

1. In Google Drive, share the existing image folder with
   `social-publisher@social-media-publisher.iam.gserviceaccount.com` as **Viewer**.
   The folder can remain private. Share shortcut targets separately if needed.
   Workspace policies must permit this sharing.
2. In GitHub -> Settings -> Secrets and variables -> Actions -> **Variables**, add the
   two values printed above: `GCP_SERVICE_ACCOUNT` and `GCP_WORKLOAD_IDENTITY_PROVIDER`.
   Set both together. Keep `GOOGLE_DRIVE_FOLDER_ID` and `GEMINI_API_KEY` in Secrets.
3. Merge the code change, then run **Publish condo social post** on `main` with
   `publish` unchecked. Verify the chosen image and caption in the output. This dry-run
   reads Drive and calls Gemini; it does not post to Meta.
4. After that succeeds, remove the unused `GDRIVE_CLIENT_ID`, `GDRIVE_CLIENT_SECRET`,
   and `GDRIVE_REFRESH_TOKEN` Actions secrets. Scheduled Facebook publishing retains its
   existing behavior; Instagram remains disabled for scheduled publishing.

To roll back, remove both federation repository variables and restore the three legacy
OAuth secrets if removed. The workflow then uses the existing OAuth mode.

## Local runs

The default remains `GDRIVE_AUTH_MODE=oauth` for compatibility. To use runtime credentials
locally, set `GDRIVE_AUTH_MODE=adc` and supply valid Application Default Credentials with
the Drive read-only scope. GitHub creates its own credential configuration automatically;
never copy `gha-creds-*.json` from a runner or commit credential files.

If retaining personal OAuth, Google's external consent apps in Testing normally issue
Drive refresh tokens that expire in seven days. Production status removes that particular
limit, but tokens can still be revoked. Federation avoids personal consent tokens here.

## Facebook and Instagram are separate

Google authentication does not renew `META_ACCESS_TOKEN`. The existing publisher expects
a Facebook Page-capable token. Use Meta's supported long-lived Page-token flow, or assess
a Business Portfolio system-user flow for an app and assets you own. Confirm the token
type, publishing permissions, asset assignments, expiry, and data-access expiry with
Meta's Access Token Debugger before changing the secret. Availability depends on the
app's configuration and permissions; this change does not claim Meta is fixed.

Even a token reported as having no scheduled expiry can be revoked by permission or
business changes. Do not schedule user-token exchanges as a supposed permanent fix:
Meta and Google have different token lifecycles. Never paste tokens or app secrets into
issues, pull requests, or chat.

## References

- [Google deployment pipeline federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
- [Google GitHub authentication action](https://github.com/google-github-actions/auth)
- [Sharing Drive folders with service accounts](https://workspace.google.com/blog/developers-practitioners/dont-fear-authentication-google-drive-edition)
- [Google OAuth refresh token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)
- [Meta access tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/)
- [Meta Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
