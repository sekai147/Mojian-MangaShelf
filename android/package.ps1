param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
if(!$SkipBuild){& "$PSScriptRoot\build.ps1"}
$release=Join-Path $project 'release\android'
$stage=Join-Path $PSScriptRoot ('build\package-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force "$stage\android\app", "$stage\android\tests" | Out-Null
# Explicit source whitelist excludes SDKs, build output, test data and signing secrets.
foreach($file in @('README.md','安装说明.txt','build.gradle','settings.gradle','build.ps1','package.ps1')){
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination "$stage\android" -Force
}
Copy-Item -LiteralPath "$PSScriptRoot\app\src" -Destination "$stage\android\app" -Recurse
Copy-Item -LiteralPath "$PSScriptRoot\app\build.gradle" -Destination "$stage\android\app"
foreach($file in @('build.ps1','run.ps1','AndroidManifest.xml')){Copy-Item -LiteralPath "$PSScriptRoot\tests\$file" -Destination "$stage\android\tests"}
Copy-Item -LiteralPath "$PSScriptRoot\tests\java" -Destination "$stage\android\tests" -Recurse
foreach($file in @('LICENSE.txt','AGPL-3.0.txt')){Copy-Item -LiteralPath "$project\$file" -Destination $stage}
Copy-Item -LiteralPath "$PSScriptRoot\安装说明.txt" -Destination $release -Force
Copy-Item -LiteralPath "$PSScriptRoot\README.md" -Destination "$release\安卓使用说明.md" -Force
$zip=Join-Path $release 'Mojian-Android-1.1.1-source.zip'
Compress-Archive -Path "$stage\*" -DestinationPath $zip -CompressionLevel Optimal -Force
Write-Output "Source archive: $zip"
