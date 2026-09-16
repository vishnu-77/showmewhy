$ErrorActionPreference = 'Stop'

$RepoUrl = if ($env:SHOWMEWHY_REPO_URL) { $env:SHOWMEWHY_REPO_URL } else { 'https://github.com/vishnu-77/showmewhy.git' }
$MarketplaceSource = if ($env:SHOWMEWHY_MARKETPLACE_SOURCE) { $env:SHOWMEWHY_MARKETPLACE_SOURCE } else { $RepoUrl }
$SourceDir = $env:SHOWMEWHY_SOURCE_DIR
$ClaudeHome = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $HOME '.claude' }
$SkillDest = Join-Path $ClaudeHome 'skills\showmewhy'
$ArchiveUrl = if ($env:SHOWMEWHY_ARCHIVE_URL) { $env:SHOWMEWHY_ARCHIVE_URL } else { 'https://github.com/vishnu-77/showmewhy/archive/refs/heads/main.zip' }
$TempDir = $null

function Write-Step([string]$Message) {
    Write-Host $Message
}

function Invoke-Claude([string[]]$Arguments) {
    & claude @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "claude $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

try {
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

    Write-Step 'Installing ShowMeWhy runtime...'
    & claude plugin uninstall showmewhy@showmewhy *> $null
    & claude plugin marketplace remove showmewhy *> $null
    Invoke-Claude @('plugin', 'marketplace', 'add', $MarketplaceSource)
    Invoke-Claude @('plugin', 'install', 'showmewhy@showmewhy')

    if ($SourceDir) {
        $SkillSource = Join-Path $SourceDir 'standalone\showmewhy'
    }
    else {
        $TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("showmewhy-" + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
        $ZipPath = Join-Path $TempDir 'showmewhy.zip'
        Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ZipPath
        Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force
        $SkillSource = Get-ChildItem -Path $TempDir -Directory -Recurse |
            Where-Object { $_.FullName -match '[\\/]standalone[\\/]showmewhy$' } |
            Select-Object -First 1 -ExpandProperty FullName
    }

    if (-not $SkillSource -or -not (Test-Path (Join-Path $SkillSource 'SKILL.md'))) {
        throw 'Standalone Skill source was not found.'
    }

    Write-Step 'Installing /showmewhy globally...'
    $SkillParent = Split-Path $SkillDest -Parent
    New-Item -ItemType Directory -Path $SkillParent -Force | Out-Null
    if (Test-Path $SkillDest) {
        Remove-Item -Path $SkillDest -Recurse -Force
    }
    Copy-Item -Path $SkillSource -Destination $SkillDest -Recurse -Force

    $InstalledSkill = Join-Path $SkillDest 'SKILL.md'
    if (-not (Test-Path $InstalledSkill)) {
        throw 'Global Skill installation failed.'
    }
    if (-not (Select-String -Path $InstalledSkill -Pattern '^name: showmewhy$' -Quiet)) {
        throw 'Installed Skill failed its identity check.'
    }

    $PluginList = (& claude plugin list 2>$null | Out-String)
    if ($PluginList -notmatch 'showmewhy@showmewhy') {
        throw 'Runtime plugin is not registered after installation.'
    }

    Write-Host ''
    Write-Step 'ShowMeWhy installed.'
    Write-Step '  command  /showmewhy'
    Write-Step "  skill    $SkillDest"
    Write-Step '  runtime  showmewhy@showmewhy'
    Write-Host ''
    Write-Step 'Start a new Claude Code session and type /showmewhy.'
}
finally {
    if ($TempDir -and (Test-Path $TempDir)) {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
