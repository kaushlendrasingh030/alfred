param(
    [Parameter(Mandatory=$false)]
    [string]$RemoteUrl
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is not installed or not on PATH. Install Git first."
    exit 1
}

if (-not (Test-Path .git)) {
    git init
}

git add .
# use local config for commit to avoid global missing config issues
git -c user.name="alfred-bot" -c user.email="alfred@example.com" commit -m "Initial commit: add alfred assistant"

if ($RemoteUrl) {
    git remote remove origin -ErrorAction SilentlyContinue | Out-Null
    git remote add origin $RemoteUrl
}

if (-not $RemoteUrl) {
    Write-Host "No remote URL provided. To push, call this script with the repo URL: .\push_to_github.ps1 -RemoteUrl 'https://github.com/username/repo.git'"
    exit 0
}

try {
    git push -u origin main
} catch {
    Write-Host "Push failed. If your default branch is 'master' try: git push -u origin master"
    throw $_
}
