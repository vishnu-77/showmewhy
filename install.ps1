$ErrorActionPreference = 'Stop'

$RepoUrl = if ($env:SHOWMEWHY_REPO_URL) { $env:SHOWMEWHY_REPO_URL } else { 'https://github.com/vishnu-77/showmewhy.git' }
$MarketplaceSource = if ($env:SHOWMEWHY_MARKETPLACE_SOURCE) { $env:SHOWMEWHY_MARKETPLACE_SOURCE } else { $RepoUrl }
$ClaudeHome = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $HOME '.claude' }
$KnownMarketplaces = Join-Path $ClaudeHome 'plugins\known_marketplaces.json'
$LegacySkill = Join-Path $ClaudeHome 'skills\showmewhy'

function Write-Step([string]$Message) {
    Write-Host $Message
}

function Invoke-Claude([string[]]$Arguments) {
    & claude @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "claude $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Step "Claude Code not found. Installing Anthropic's stable native build..."
    & ([scriptblock]::Create((Invoke-RestMethod 'https://claude.ai/install.ps1'))) stable
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    $LocalBin = Join-Path $HOME '.local\bin'
    $env:PATH = "$LocalBin;$env:PATH"
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw 'Claude Code installation was not found on PATH.'
}

$env:CLAUDE_CODE_PLUGIN_PREFER_HTTPS = '1'

Write-Step 'Installing ShowMeWhy...'
& claude plugin uninstall showmewhy@showmewhy *> $null
& claude plugin marketplace remove showmewhy *> $null
Invoke-Claude @('plugin', 'marketplace', 'add', $MarketplaceSource)

if (-not (Test-Path $KnownMarketplaces)) {
    throw "Claude marketplace state was not created at $KnownMarketplaces."
}

$state = Get-Content $KnownMarketplaces -Raw | ConvertFrom-Json
if (-not $state.showmewhy) {
    throw 'ShowMeWhy marketplace registration was not found.'
}
$state.showmewhy | Add-Member -NotePropertyName autoUpdate -NotePropertyValue $true -Force
$state | ConvertTo-Json -Depth 20 | Set-Content -Path $KnownMarketplaces -Encoding utf8

# Remove the copied personal Skill from the 4.1.0 distribution model. The Skill
# now ships inside the marketplace plugin so code and prompt contract update atomically.
if (Test-Path $LegacySkill) {
    Remove-Item -Path $LegacySkill -Recurse -Force
}

Invoke-Claude @('plugin', 'install', 'showmewhy@showmewhy')

$plugins = (& claude plugin list 2>$null | Out-String)
if ($plugins -notmatch 'showmewhy@showmewhy') {
    throw 'ShowMeWhy plugin is not registered after installation.'
}

$state = Get-Content $KnownMarketplaces -Raw | ConvertFrom-Json
if ($state.showmewhy.autoUpdate -ne $true) {
    throw 'ShowMeWhy marketplace auto-update is not enabled.'
}

Write-Host ''
Write-Step 'ShowMeWhy installed with marketplace auto-update enabled.'
Write-Step '  plugin   showmewhy@showmewhy'
Write-Step '  command  /showmewhy:showmewhy'
Write-Step '  updates  automatic on Claude startup when upstream changes'
Write-Host ''
Write-Step 'Restart Claude Code once after this installation.'
