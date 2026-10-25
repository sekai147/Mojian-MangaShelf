param([switch]$Test, [string]$JavaHomePath=$env:JAVA_HOME, [string]$AndroidSdkPath=$env:ANDROID_HOME)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$tools = Join-Path $project '.tools\android'
New-Item -ItemType Directory -Force $tools | Out-Null
$javaHome = $JavaHomePath
if (!$javaHome) { $javaHome = (Get-ChildItem -LiteralPath $tools -Directory -Filter 'jdk-*' | Select-Object -First 1).FullName }
if ($AndroidSdkPath) {
    $platform = Join-Path $AndroidSdkPath 'platforms\android-35\android.jar'
    $aapt = Join-Path $AndroidSdkPath 'build-tools\35.0.0\aapt2.exe'
} else {
    $platform = (Get-ChildItem -LiteralPath (Join-Path $tools 'platform') -Recurse -Filter android.jar | Select-Object -First 1).FullName
    $aapt = (Get-ChildItem -LiteralPath (Join-Path $tools 'build-tools') -Recurse -Filter aapt2.exe | Select-Object -First 1).FullName
}
if (!$javaHome -or !$platform -or !$aapt) { throw 'Missing JDK or Android SDK. See android/README.md.' }
$bin = Split-Path $aapt -Parent
$env:JAVA_HOME = $javaHome
$env:PATH = "$javaHome\bin;$env:SystemRoot\System32;$env:SystemRoot"
$out = Join-Path $PSScriptRoot 'build'
foreach ($part in @('classes','dex','generated')) {
    $directory=Join-Path $out $part
    if(Test-Path -LiteralPath $directory) {
        $resolved=(Resolve-Path -LiteralPath $directory).Path
        if($resolved -ne [IO.Path]::GetFullPath($directory) -or !$resolved.StartsWith([IO.Path]::GetFullPath($PSScriptRoot)+[IO.Path]::DirectorySeparatorChar)) { throw 'Invalid build cleanup path' }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
New-Item -ItemType Directory -Force $out, "$out\classes", "$out\dex", "$out\generated" | Out-Null
function Run([string]$program, [string[]]$arguments) {
    & $program @arguments
    if ($LASTEXITCODE -ne 0) { throw "$program failed with exit $LASTEXITCODE" }
}
$src = Join-Path $PSScriptRoot 'app\src\main'
Run $aapt @('compile','--dir',"$src\res",'-o',"$out\resources.zip")
Run $aapt @('link','-o',"$out\base.apk",'--manifest',"$src\AndroidManifest.xml",'-I',$platform,'--java',"$out\generated",'--auto-add-overlay',"$out\resources.zip")
$sources = @((Get-ChildItem "$src\java" -Recurse -Filter '*.java').FullName) + @((Get-ChildItem "$out\generated" -Recurse -Filter '*.java').FullName)
Run "$javaHome\bin\javac.exe" (@('-encoding','UTF-8','--release','8','-classpath',$platform,'-d',"$out\classes") + $sources)
Run "$javaHome\bin\jar.exe" @('cf',"$out\classes.jar",'-C',"$out\classes",'.')
Run "$bin\d8.bat" @('--release','--min-api','26','--lib',$platform,'--output',"$out\dex","$out\classes.jar")
Copy-Item -LiteralPath "$out\base.apk" -Destination "$out\unsigned.apk" -Force
Run "$javaHome\bin\jar.exe" @('uf',"$out\unsigned.apk",'-C',"$out\dex",'classes.dex')
Run "$bin\zipalign.exe" @('-f','-p','4',"$out\unsigned.apk","$out\aligned.apk")
$key = Join-Path $tools 'mojian-release.p12'
$passwordFile = Join-Path $tools 'signing-password.txt'
if (!(Test-Path -LiteralPath $key)) {
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 32
    $rng.GetBytes($bytes)
    [IO.File]::WriteAllText($passwordFile,[Convert]::ToBase64String($bytes),[Text.UTF8Encoding]::new($false))
    # Keep this local release identity for compatible APK upgrades; never include it in a source archive.
    Run "$javaHome\bin\keytool.exe" @('-genkeypair','-keystore',$key,'-storetype','PKCS12','-storepass:file',$passwordFile,'-alias','mojian','-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=MoJian Android, O=MangaShelf, C=CN')
}
$release = Join-Path $project 'release\android'
New-Item -ItemType Directory -Force $release | Out-Null
$apk = Join-Path $release 'Mojian-Android-1.1.1.apk'
Run "$bin\apksigner.bat" @('sign','--ks',$key,'--ks-key-alias','mojian','--ks-pass',"file:$passwordFile",'--out',$apk,"$out\aligned.apk")
Run "$bin\apksigner.bat" @('verify','--verbose',$apk)
$hash=(Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText("$apk.sha256","$hash  $([IO.Path]::GetFileName($apk))`n",[Text.UTF8Encoding]::new($false))
Write-Output "APK: $apk"
if ($Test) { & (Join-Path $PSScriptRoot 'tests\build.ps1') -JavaHomePath $javaHome -AndroidSdkPath $AndroidSdkPath }
