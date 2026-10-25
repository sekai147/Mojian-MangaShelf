param(
    [Parameter(Mandatory=$true)][string]$AdbPath,
    [Parameter(Mandatory=$true)][string]$Serial,
    [Parameter(Mandatory=$true)][switch]$DisposableDevice
)
$ErrorActionPreference='Stop'
if(!$DisposableDevice){throw 'Use a disposable emulator without personal app data.'}
$android=Split-Path $PSScriptRoot -Parent
$project=Split-Path $android -Parent
function Adb([string[]]$arguments){ & $AdbPath -s $Serial @arguments; if($LASTEXITCODE -ne 0){throw 'adb failed'} }
$existing=Adb @('shell','pm','list','packages','com.mangashelf.mojian')
if($existing -match 'package:com.mangashelf.mojian'){throw 'The app is already installed. Use a fresh disposable emulator; this script will not clear an existing library.'}
& "$android\build.ps1" -Test
$installed=$false;$testInstalled=$false
$out=Join-Path $project ('test-output\android-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $out | Out-Null
try {
    Adb @('install','--no-incremental',"$project\release\android\Mojian-Android-1.1.1.apk")
    $installed=$true
    Adb @('install','--no-incremental',"$android\build\tests\tests.apk")
    $testInstalled=$true
    $output=Adb @('shell','am','instrument','-w','com.mangashelf.mojian.tests/com.mangashelf.mojian.ReaderInstrumentation')
    $output | Set-Content -LiteralPath "$out\instrumentation.txt" -Encoding utf8
    Adb @('pull','/sdcard/Android/data/com.mangashelf.mojian/files',"$out\capture")
    if(($output -join "`n") -notmatch '16 checks passed'){throw "Android verification failed; see $out"}
    $webtoon=Adb @('shell','am','instrument','-w','com.mangashelf.mojian.tests/com.mangashelf.mojian.WebtoonInstrumentation')
    $webtoon | Set-Content -LiteralPath "$out\webtoon.txt" -Encoding utf8
    Adb @('pull','/sdcard/Android/data/com.mangashelf.mojian/files',"$out\webtoon-capture")
    if(($webtoon -join "`n") -notmatch '10 webtoon checks passed'){throw "Webtoon verification failed; see $out"}
    $toolbar=Adb @('shell','am','instrument','-w','com.mangashelf.mojian.tests/com.mangashelf.mojian.ChromeInstrumentation')
    $toolbar | Set-Content -LiteralPath "$out\toolbar.txt" -Encoding utf8
    if(($toolbar -join "`n") -notmatch '6 toolbar checks passed'){throw "Toolbar verification failed; see $out"}
    Write-Output "32 Android checks passed. Evidence: $out"
} finally {
    if($testInstalled){Adb @('uninstall','com.mangashelf.mojian.tests')}
    if($installed){Adb @('uninstall','com.mangashelf.mojian')}
}
