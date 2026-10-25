param([string]$ReleaseName = '墨间漫画阅读器')
$ErrorActionPreference = 'Stop'
if ([IO.Path]::GetFileName($ReleaseName) -ne $ReleaseName -or $ReleaseName -in @('.','..','')) {
    throw 'ReleaseName must be a single directory name'
}
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$basePythonPath = (& $pythonPath -c 'import sys; print(sys.base_prefix)').Trim()
& $pythonPath (Join-Path $PSScriptRoot 'scripts\build_icon.py')
if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed' }
$iconAssets = Join-Path $PSScriptRoot 'mangashelf\assets'
$exeIcon = Join-Path $iconAssets 'mangashelf.ico'
$previousBuildPath = $env:PATH
try {
    # Keep unrelated toolchain DLLs (e.g. Poppler's ICU) out of dependency discovery.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$basePythonPath;$basePythonPath\Scripts"
    & $pythonPath -m PyInstaller --clean --noconfirm --windowed --onedir --name MangaShelf --icon $exeIcon --add-data "${iconAssets};mangashelf/assets" --exclude-module onnxruntime --exclude-module numpy --exclude-module networkx --exclude-module pymupdf4llm --exclude-module pymupdf_layout run.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
} finally {
    $env:PATH = $previousBuildPath
}
$releasePath = Join-Path (Join-Path $PSScriptRoot 'release') $ReleaseName
New-Item -ItemType Directory -Path $releasePath -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $releasePath 'comics') -Force | Out-Null
$internalPath = Join-Path $releasePath '_internal'
if (Test-Path -LiteralPath $internalPath) {
    $resolvedInternal = (Resolve-Path -LiteralPath $internalPath).Path
    $expectedInternal = [IO.Path]::GetFullPath((Join-Path $releasePath '_internal'))
    if ($resolvedInternal -ne $expectedInternal) { throw 'Unexpected runtime output path' }
    Remove-Item -LiteralPath $resolvedInternal -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'dist\MangaShelf\MangaShelf.exe') -Destination $releasePath -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'dist\MangaShelf\_internal') -Destination $releasePath -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.md') -Destination (Join-Path $releasePath '使用说明.md') -Force
foreach ($licenseName in @('LICENSE.txt','AGPL-3.0.txt','GPL-3.0.txt','LGPL-3.0.txt')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $licenseName) -Destination $releasePath -Force
}
$sourcePath = Join-Path $releasePath 'source'
New-Item -ItemType Directory -Path (Join-Path $sourcePath 'mangashelf') -Force | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot 'mangashelf\*.py') -Destination (Join-Path $sourcePath 'mangashelf') -Force
Copy-Item -LiteralPath $iconAssets -Destination (Join-Path $sourcePath 'mangashelf') -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $sourcePath 'scripts') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'scripts\build_icon.py') -Destination (Join-Path $sourcePath 'scripts') -Force
New-Item -ItemType Directory -Path (Join-Path $sourcePath 'tests') -Force | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot 'tests\*.py') -Destination (Join-Path $sourcePath 'tests') -Force
foreach ($sourceName in @('run.py','requirements.txt','README.md','build.ps1','LICENSE.txt','AGPL-3.0.txt','GPL-3.0.txt','LGPL-3.0.txt')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $sourceName) -Destination $sourcePath -Force
}
Write-Output "Built: $releasePath"
