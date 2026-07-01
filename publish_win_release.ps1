# Publish Windows release for PolyWav Merger 4.0.1-beta
# Prerequisite: gh auth login
$ErrorActionPreference = "Stop"
$env:Path = "C:\Program Files\GitHub CLI;" + $env:Path

$repo = "RostislavAtmo/PolyWav-Merger-by-Atmo"
$tag = "v4.0.1-beta"
$title = "PolyWav Merger Beta 4.0.1"
$notesFile = "RELEASE_NOTES_4.0.1-beta.md"
$installer = "dist_merged\PolyWav_Merger_Setup_4.0.1-beta.exe"
$portable = "dist_merged\polywav_merger.exe"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) not found. Install from https://cli.github.com/"
}

foreach ($f in @($installer, $portable, $notesFile)) {
    if (-not (Test-Path $f)) { throw "Missing file: $f" }
}

gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub CLI is not authenticated."
    Write-Host "Run once: gh auth login"
    Write-Host "Then rerun: powershell -ExecutionPolicy Bypass -File publish_win_release.ps1"
    exit 1
}

# Create or update the release and upload Windows assets
gh release view $tag --repo $repo 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    gh release create $tag `
        --repo $repo `
        --title $title `
        --notes-file $notesFile `
        --prerelease `
        $installer $portable
} else {
    gh release upload $tag `
        --repo $repo `
        --clobber `
        $installer $portable
    gh release edit $tag `
        --repo $repo `
        --title $title `
        --notes-file $notesFile `
        --prerelease
}

Write-Host "Done: https://github.com/$repo/releases/tag/$tag"
