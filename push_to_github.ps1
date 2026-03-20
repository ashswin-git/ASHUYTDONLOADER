$ErrorActionPreference = 'Stop'

Write-Host "Creating GitHub Repository..."
$headers = @{
    "Authorization" = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("ashswin-git:sDazkqBGMrpEa9Wn6pjkUxbB"))
    "Accept" = "application/vnd.github.v3+json"
    "User-Agent" = "PowerShell"
}

$body = @{
    "name" = "Universal-Downloader"
    "description" = "Universal social media downloader ready for Vercel deployment"
    "private" = $false
} | ConvertTo-Json

# Check if repo exists first or just create it
try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body
    Write-Host "Repository created successfully at $($response.html_url)"
} catch {
    Write-Host "Repository might already exist, continuing to push phase..."
}

Write-Host "Initializing local git..."
git init
git add .
git commit -m "Initial release of Vercel-ready Universal Downloader"
git branch -M main
git remote remove origin 2>$null
git remote add origin "https://ashswin-git:sDazkqBGMrpEa9Wn6pjkUxbB@github.com/ashswin-git/Universal-Downloader.git"

Write-Host "Pushing code to GitHub..."
git push -u origin main

Write-Host "Perfect! The code has been fully pushed to GitHub."
