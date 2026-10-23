#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef BundleDir
  #error BundleDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif

[Setup]
AppId={{DF75F937-A706-4914-AD61-06D18713CD62}
AppName=GitHub 每日项目推送
AppVersion={#AppVersion}
AppPublisher=GitHub Daily Press
AppPublisherURL=https://github.com/0505ttt/github-daily-press
DefaultDirName={localappdata}\Programs\GitHubDailyPress
DefaultGroupName=GitHub 每日项目推送
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=GitHubDailyPress-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\GitHubDailyPress.exe
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GitHub 每日项目推送"; Filename: "{app}\GitHubDailyPress.exe"
Name: "{autodesktop}\GitHub 每日项目推送"; Filename: "{app}\GitHubDailyPress.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GitHubDailyPress.exe"; Description: "打开 GitHub 每日项目推送"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  RuntimeVersion: String;
  RuntimeKey: String;
  ResultCode: Integer;
begin
  RuntimeKey := 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result := True;
  if not (RegQueryStringValue(HKCU, RuntimeKey, 'pv', RuntimeVersion) and
          (RuntimeVersion <> '') and (RuntimeVersion <> '0.0.0.0')) then
    if not (RegQueryStringValue(HKLM32, RuntimeKey, 'pv', RuntimeVersion) and
            (RuntimeVersion <> '') and (RuntimeVersion <> '0.0.0.0')) then
      if not (RegQueryStringValue(HKLM64, RuntimeKey, 'pv', RuntimeVersion) and
              (RuntimeVersion <> '') and (RuntimeVersion <> '0.0.0.0')) then
      begin
        MsgBox('本应用需要 Microsoft Edge WebView2 Runtime。Windows 11 通常已内置；若尚未安装，请先从 Microsoft 官方网站安装，再运行本安装包。', mbInformation, MB_OK);
        ShellExec('open', 'https://developer.microsoft.com/microsoft-edge/webview2/', '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
        Result := False;
      end;
end;
