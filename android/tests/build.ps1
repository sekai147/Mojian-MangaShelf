param([string]$JavaHomePath=$env:JAVA_HOME, [string]$AndroidSdkPath=$env:ANDROID_HOME)
$ErrorActionPreference = 'Stop'
$android = Split-Path $PSScriptRoot -Parent
$project = Split-Path $android -Parent
$tools = Join-Path $project '.tools\android'
$java = $JavaHomePath
if(!$java){$java=(Get-ChildItem $tools -Directory -Filter 'jdk-*' | Select-Object -First 1).FullName}
if($AndroidSdkPath){$platform=Join-Path $AndroidSdkPath 'platforms\android-35\android.jar';$aapt=Join-Path $AndroidSdkPath 'build-tools\35.0.0\aapt2.exe'}
else{$platform=(Get-ChildItem "$tools\platform" -Recurse -Filter android.jar | Select-Object -First 1).FullName;$aapt=(Get-ChildItem "$tools\build-tools" -Recurse -Filter aapt2.exe | Select-Object -First 1).FullName}
$bin = Split-Path $aapt -Parent
$env:JAVA_HOME=$java
$env:PATH="$java\bin;$env:SystemRoot\System32;$env:SystemRoot"
$out=Join-Path $android 'build\tests'
New-Item -ItemType Directory -Force "$out\classes","$out\dex" | Out-Null
function Run([string]$program,[string[]]$arguments){ & $program @arguments; if($LASTEXITCODE -ne 0){throw "$program failed"} }
Run $aapt @('link','-o',"$out\base.apk",'--manifest',"$PSScriptRoot\AndroidManifest.xml",'-I',$platform)
$sources=@((Get-ChildItem "$PSScriptRoot\java" -Recurse -Filter '*.java').FullName)
Run "$java\bin\javac.exe" (@('-encoding','UTF-8','--release','8','-classpath',"$platform;$android\build\classes",'-d',"$out\classes")+$sources)
Run "$java\bin\jar.exe" @('cf',"$out\classes.jar",'-C',"$out\classes",'.')
Run "$bin\d8.bat" @('--release','--min-api','26','--lib',$platform,'--classpath',"$android\build\classes.jar",'--output',"$out\dex","$out\classes.jar")
Run "$java\bin\jar.exe" @('uf',"$out\base.apk",'-C',"$out\dex",'classes.dex')
Run "$bin\zipalign.exe" @('-f','4',"$out\base.apk","$out\aligned.apk")
Run "$bin\apksigner.bat" @('sign','--ks',"$tools\mojian-release.p12",'--ks-key-alias','mojian','--ks-pass',"file:$tools\signing-password.txt",'--out',"$out\tests.apk","$out\aligned.apk")
Write-Output "Instrumentation APK: $out\tests.apk"
