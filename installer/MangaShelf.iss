#ifndef SourceDir
  #error SourceDir must point to a built application directory
#endif
#ifndef ProjectDir
  #define ProjectDir AddBackslash(SourcePath) + ".."
#endif
#ifndef InstallerOutput
  #define InstallerOutput AddBackslash(ProjectDir) + "release\installer"
#endif
#ifndef AppVersion
  #define AppVersion "1.4.1"
#endif

[Setup]
AppId=MoJian.MangaShelf
AppName=墨间漫画阅读器
AppVersion={#AppVersion}
AppPublisher=MangaShelf
AppComments=本地 PDF 漫画书库与双页阅读器
DefaultDirName={localappdata}\Programs\MangaShelf
DefaultGroupName=墨间漫画阅读器
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UsePreviousAppDir=yes
DisableDirPage=no
DisableProgramGroupPage=auto
AllowNoIcons=yes
DisableWelcomePage=no
WizardStyle=modern
WizardSizePercent=110
WizardImageFile={#ProjectDir}\installer\assets\wizard-1x.bmp,{#ProjectDir}\installer\assets\wizard-2x.bmp
WizardSmallImageFile={#ProjectDir}\installer\assets\wizard-small.bmp
SetupIconFile={#ProjectDir}\mangashelf\assets\mangashelf.ico
UninstallDisplayIcon={app}\MangaShelf.exe
UninstallDisplayName=墨间漫画阅读器
LicenseFile={#ProjectDir}\LICENSE.txt
OutputDir={#InstallerOutput}
OutputBaseFilename=MangaShelf-Setup-{#AppVersion}-x64
Compression=lzma2/normal
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#AppVersion}
VersionInfoProductName=墨间漫画阅读器
VersionInfoDescription=墨间漫画阅读器安装程序
VersionInfoCompany=MangaShelf

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Dirs]
Name: "{app}\comics"; Flags: uninsneveruninstall
Name: "{app}\data"; Flags: uninsneveruninstall

[Files]
Source: "{#SourceDir}\MangaShelf.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\source\*"; DestDir: "{app}\source"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectDir}\README.md"; DestDir: "{app}"; DestName: "使用说明.md"; Flags: ignoreversion
Source: "{#ProjectDir}\installer\安装说明.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\AGPL-3.0.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\GPL-3.0.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\LGPL-3.0.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectDir}\installer\*"; DestDir: "{app}\source\installer"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectDir}\build_installer.ps1"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "{#ProjectDir}\scripts\build_installer_art.py"; DestDir: "{app}\source\scripts"; Flags: ignoreversion

[Icons]
Name: "{group}\墨间漫画阅读器"; Filename: "{app}\MangaShelf.exe"; WorkingDir: "{app}"; AppUserModelID: "MangaShelf.Mojian.Reader"
Name: "{autodesktop}\墨间漫画阅读器"; Filename: "{app}\MangaShelf.exe"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "MangaShelf.Mojian.Reader"

[Run]
Filename: "{app}\MangaShelf.exe"; Description: "启动墨间漫画阅读器"; Flags: nowait postinstall skipifsilent

[Messages]
WelcomeLabel1=欢迎安装墨间漫画阅读器
WelcomeLabel2=一个安静的本地漫画书库。%n%n支持 PDF 文件夹导入、章节自动排序、双页阅读和进度记忆。%n%n点击“下一步”开始安装。
FinishedLabel=墨间已安装完成。%n%n通过开始菜单或桌面快捷方式即可打开。%n%n漫画保存在安装目录的 comics 文件夹，阅读进度保存在 data 文件夹。卸载程序时会保留这两个文件夹。%n%n已有便携版可将 comics 和 data 文件夹复制到安装目录，自动恢复漫画库与进度。
UninstalledAll=墨间已成功卸载。%n%n漫画文件和阅读进度保留在原安装目录的 comics 和 data 文件夹中。
