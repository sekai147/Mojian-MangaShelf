param(
    [string]$ReleaseName = '墨间漫画阅读器',
    [string]$CompilerPath = ''
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ([IO.Path]::GetFileName($ReleaseName) -ne $ReleaseName -or $ReleaseName -in @('.','..','')) {
    throw 'ReleaseName must be a single directory name'
}
if (-not $CompilerPath) { $CompilerPath = Join-Path $PSScriptRoot '.tools\inno\ISCC.exe' }
if (-not (Test-Path -LiteralPath $CompilerPath)) {
    throw 'Inno Setup ISCC.exe not found. Pass -CompilerPath with its full path.'
}
$payloadPath = Join-Path (Join-Path $PSScriptRoot 'release') $ReleaseName
foreach ($required in @('MangaShelf.exe','_internal','source\mangashelf\__init__.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $payloadPath $required))) {
        throw "Build the application first; payload missing: $required"
    }
}
$versionFile = Get-Content -LiteralPath (Join-Path $payloadPath 'source\mangashelf\__init__.py') -Raw
if ($versionFile -notmatch '__version__\s*=\s*"(\d+\.\d+\.\d+)"') { throw 'Missing application version' }
$appVersion = $Matches[1]
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'scripts\build_installer_art.py')
if ($LASTEXITCODE -ne 0) { throw 'Installer artwork generation failed' }
$installerOutput = Join-Path $PSScriptRoot 'release\installer'
New-Item -ItemType Directory -Path $installerOutput -Force | Out-Null
& $CompilerPath "-DSourceDir=$payloadPath" "-DProjectDir=$PSScriptRoot" "-DInstallerOutput=$installerOutput" "-DAppVersion=$appVersion" (Join-Path $PSScriptRoot 'installer\MangaShelf.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
$setupFile = Join-Path $installerOutput "MangaShelf-Setup-$appVersion-x64.exe"
$checksum = (Get-FileHash -LiteralPath $setupFile -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText("$setupFile.sha256","$checksum  $([IO.Path]::GetFileName($setupFile))`n",[Text.UTF8Encoding]::new($false))
Write-Output "Installer: $setupFile"
