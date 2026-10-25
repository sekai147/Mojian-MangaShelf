param([string]$InstallerPath = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not $InstallerPath) { $InstallerPath = Join-Path $projectRoot 'release\installer\MangaShelf-Setup-1.4.1-x64.exe' }
$appRegistryKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MoJian.MangaShelf_is1'
if (Test-Path -LiteralPath $appRegistryKey) { throw 'An installed copy already exists; refusing to change its registration.' }
$runId = [Guid]::NewGuid().ToString('N')
$testRoot = Join-Path $projectRoot "test-output\installer-$runId"
$appRoot = Join-Path $testRoot '墨间 安装测试'
$groupName = 'MoJian Installer Test '+$runId
$shortcutDirectory = Join-Path ([Environment]::GetFolderPath('Programs')) $groupName
if (Test-Path -LiteralPath $shortcutDirectory) { throw 'Unexpected existing test shortcut directory' }
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$resolvedTestRoot = (Resolve-Path -LiteralPath $testRoot).Path
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'test-output')) + [IO.Path]::DirectorySeparatorChar
if (-not $resolvedTestRoot.StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected smoke-test path' }
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$fixtureScript = Join-Path $PSScriptRoot 'installer_smoke_data.py'
function Invoke-CheckedProcess([string]$Executable,[string[]]$Parameters) {
    $process = Start-Process -FilePath $Executable -ArgumentList $Parameters -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(60000)) { throw "Test process timed out: $($process.Id)" }
    if ($process.ExitCode -ne 0) { throw "Test process failed ($($process.ExitCode)): $Executable" }
}
function Install-TestCopy([string]$LogName) {
    Invoke-CheckedProcess $InstallerPath @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
        '/LANG=chinesesimplified',('/DIR="'+$appRoot+'"'),('/GROUP="'+$groupName+'"'),
        '/TASKS=""',('/LOG="'+(Join-Path $testRoot $LogName)+'"'))
}
Install-TestCopy 'install.log'
$exePath = Join-Path $appRoot 'MangaShelf.exe'
if (-not (Test-Path -LiteralPath $exePath)) { throw 'Installed executable missing' }
if (-not (Test-Path -LiteralPath $appRegistryKey)) { throw 'Uninstall registration missing' }
$shortcutPath = Join-Path $shortcutDirectory '墨间漫画阅读器.lnk'
if (-not (Test-Path -LiteralPath $shortcutPath)) { throw 'Start menu shortcut missing' }
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
if ($shortcut.TargetPath -ne $exePath -or $shortcut.WorkingDirectory -ne $appRoot) {
    throw 'Start menu shortcut points to an unexpected location'
}
$registeredDir = (Get-ItemProperty -LiteralPath $appRegistryKey).InstallLocation.TrimEnd('\')
if ($registeredDir -ne $appRoot) { throw 'Unexpected installation registration' }
$previousQtPlatform = $env:QT_QPA_PLATFORM
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    Invoke-CheckedProcess $exePath @('--self-check',('"'+(Join-Path $testRoot 'installed-check.txt')+'"'))
} finally {
    $env:QT_QPA_PLATFORM = $previousQtPlatform
}
if ((Get-Content -LiteralPath (Join-Path $testRoot 'installed-check.txt') -Raw) -notmatch 'PDF renderer: OK') {
    throw 'Installed application self-check failed'
}
& $pythonPath $fixtureScript prepare $appRoot
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare test library' }
Install-TestCopy 'upgrade.log'
& $pythonPath $fixtureScript verify $appRoot
if ($LASTEXITCODE -ne 0) { throw 'Upgrade changed user data' }
$uninstaller = Join-Path $appRoot 'unins000.exe'
Invoke-CheckedProcess $uninstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+(Join-Path $testRoot 'uninstall.log')+'"'))
if (Test-Path -LiteralPath $exePath) { throw 'Uninstall left the application executable' }
if (Test-Path -LiteralPath (Join-Path $appRoot '_internal')) { throw 'Uninstall left the runtime directory' }
if (Test-Path -LiteralPath $appRegistryKey) { throw 'Uninstall registration was not removed' }
if (Test-Path -LiteralPath $shortcutPath) { throw 'Uninstall left the start menu shortcut' }
& $pythonPath $fixtureScript verify $appRoot
if ($LASTEXITCODE -ne 0) { throw 'Uninstall changed user data' }
$report = [ordered]@{
    installer = [IO.Path]::GetFullPath($InstallerPath)
    test_root = $testRoot
    chinese_path_with_spaces = $true
    installation = 'passed'
    installed_application_launch = 'passed'
    start_menu_shortcut_target_and_cleanup = 'passed'
    upgrade_preserves_library_and_progress = 'passed'
    uninstall_preserves_library_and_progress = 'passed'
    uninstall_removes_application_and_registration = 'passed'
}
$reportPath = Join-Path $projectRoot 'release\installer\verification.json'
$report | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output ($report | ConvertTo-Json)
