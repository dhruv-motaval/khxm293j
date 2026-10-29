# Submission guide

The code package is ready for local review. The public repository, Vercel/Render deployment and unlisted video are account-side steps and are not represented as completed in this package.

## Anonymous repository setup

1. Create a **public** repository on GitHub with a random name, for example `r8k4v2nx`. Do not use the project title or your name as the repository name.
2. Do not initialise the empty repository with a README or license.
3. From PowerShell, open this extracted project folder and run:

```powershell
git init
git branch -M main
git add .
git commit -m "Build wind forecast assessment pilot"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/r8k4v2nx.git
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME` and the example repository name with your actual repository details. The repository name is anonymous/random; your GitHub account still appears as the repository owner.

## Deploy

Follow the detailed **Deployment** section in `README.md`. Deploy the backend first, then configure `VITE_API_BASE_URL` in Vercel with that backend's HTTPS URL. Verify `/health` and then open the public frontend in an incognito window. The backend may need its `CORS_ORIGINS` updated if you use a custom frontend domain.

## Before filling the submission form

- Confirm live January 2026 records load; don't submit an empty/error dashboard.
- Confirm `pytest -q` passes and `npm run build` completes in an environment with npm registry access.
- Confirm forecast vintages published after the selected cutoff are excluded.
- Confirm `FUELHH` is filtered to `WIND` and no third dataset is used for metrics.
- Record the two-part YouTube demo with the script in `docs/demo-script.md`, total duration <=10 minutes, set visibility to Unlisted, then test the link in incognito.
- Add the public GitHub URL, deployed frontend URL and video URL to the form.
