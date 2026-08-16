; Open Dictionary 安装包脚本(Inno Setup 6.3+)
;
; 编译前提:先运行 scripts/build.py 生成 dist\OpenDirectory\
; 编译命令:ISCC.exe installer\open_dictionary.iss
; 产物:dist\OpenDictionarySetup-<版本>.exe
;
; 特性:
; - 按用户安装(不需要管理员权限)
; - 安装向导最后可选择"立即下载翻译模型(623MB)",走 hf-mirror 镜像
; - 检测到模型已存在时自动跳过下载(升级/重装场景)
; - 静默测试参数:/VERYSILENT /skipmodel=1

#define MyAppName "Open Dictionary"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "bbxiudeyi"
#define MyAppExeName "OpenDictionary.exe"

[Setup]
AppId={{7A9B3C6D-5E4F-4A2B-8C1D-0E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName}(划词翻译)
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename=OpenDictionarySetup-{#MyAppVersion}

[Files]
Source: "..\dist\OpenDictionary\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式(Create desktop shortcut)"; GroupDescription: "Additional shortcuts:"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  MirrorBase = 'https://hf-mirror.com';
  OfficialBase = 'https://huggingface.co';
  ModelRepo = 'JustFrederik/nllb-200-distilled-600M-ct2-int8';
  TokenizerRepo = 'facebook/nllb-200-distilled-600M';

var
  OptionPage: TInputOptionWizardPage;
  DownloadPage: TDownloadWizardPage;

function ModelDir(Param: string): string;
begin
  Result := ExpandConstant('{userappdata}') +
    '\open-dictionary\models\nllb-200-distilled-600M-ct2-int8';
end;

function ShouldDownloadModel: Boolean;
begin
  // /skipmodel=1 用于静默测试,强制跳过
  if ExpandConstant('{param:skipmodel|0}') = '1' then begin
    Result := False;
    exit;
  end;
  Result := OptionPage.Values[0];
end;

function UseOfficialSource: Boolean;
begin
  Result := OptionPage.Values[1];
end;

function ModelAlreadyPresent: Boolean;
begin
  Result := FileExists(ModelDir('') + '\model.bin') and
    FileExists(ModelDir('') + '\tokenizer\tokenizer.json') and
    FileExists(ModelDir('') + '\config.json');
end;

function OnDownloadProgress(const Url, FileName: String; const Progress,
  ProgressMax: Int64): Boolean;
begin
  if ProgressMax <> 0 then
    Log(Format('  %s %d/%d', [FileName, Progress, ProgressMax]));
  Result := True;  // 返回 False 会中止下载
end;

procedure InitializeWizard;
begin
  OptionPage := CreateInputOptionPage(wpReady,
    '翻译模型(Translation model)',
    '是否现在下载翻译模型?',
    'NLLB-200(623MB)将保存到:' + #13#10 + ModelDir('') + #13#10#13#10 +
    '跳过也不影响安装,之后可以在软件的"设置"页随时下载(支持断点续传)。',
    False, False);
  OptionPage.Add('现在下载(推荐,使用国内镜像 hf-mirror.com)');
  OptionPage.Add('使用官方源 huggingface.co(仅当海外网络更快时勾选)');
  OptionPage.Values[0] := True;
  OptionPage.Values[1] := False;

  DownloadPage := CreateDownloadPage(
    SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc),
    @OnDownloadProgress);
end;

function NextButtonClick(PageID: Integer): Boolean;
var
  Base, TmpFile, DestDir: string;
  Ok: Boolean;
begin
  Result := True;
  if PageID <> wpReady then
    exit;
  if not ShouldDownloadModel then
    exit;
  if ModelAlreadyPresent then begin
    Log('模型已存在,跳过下载: ' + ModelDir(''));
    exit;
  end;

  Base := MirrorBase;
  if UseOfficialSource then
    Base := OfficialBase;

  DownloadPage.Clear;
  DownloadPage.ShowBaseNameInsteadOfUrl := True;
  // Add(Url, 保存名, SHA256):哈希固定了模型版本,升级模型时需同步更新
  // 模型三件套 → 模型根目录
  DownloadPage.Add(Base + '/' + ModelRepo + '/resolve/main/model.bin',
    'model.bin', 'ed1beaf75134de7505315a5223162f56acff397eff6b50638a500d3936fe707b');
  DownloadPage.Add(Base + '/' + ModelRepo + '/resolve/main/shared_vocabulary.txt',
    'shared_vocabulary.txt', 'a132a83330f45514c2476eb81d1d69b3c41762264d16ce0a7ea982e5d6c728e5');
  DownloadPage.Add(Base + '/' + ModelRepo + '/resolve/main/config.json',
    'config.json', '0c2f6fa2057c7264d052fb4a62ba3476eeae70487acddfa8e779a53a00cbf44c');
  // 分词器四件套 → tokenizer 子目录
  DownloadPage.Add(Base + '/' + TokenizerRepo + '/resolve/main/sentencepiece.bpe.model',
    'sentencepiece.bpe.model', '14bb8dfb35c0ffdea7bc01e56cea38b9e3d5efcdcb9c251d6b40538e1aab555a');
  DownloadPage.Add(Base + '/' + TokenizerRepo + '/resolve/main/tokenizer_config.json',
    'tokenizer_config.json', 'd1aa8c3697d3e35674f97b5b7e9c99d22b010f528e80140257d97316be90d044');
  DownloadPage.Add(Base + '/' + TokenizerRepo + '/resolve/main/special_tokens_map.json',
    'special_tokens_map.json', '992bd4ed610d644d6823081937bcc91bb8878dd556cea4ae5327f2480361330e');
  DownloadPage.Add(Base + '/' + TokenizerRepo + '/resolve/main/tokenizer.json',
    'tokenizer.json', 'e316b82de11d0f951f370943b3c438311629547285129b0b81dadabd01bca665');

  DownloadPage.Show;
  try
    try
      DownloadPage.Download;
      Ok := True;
    except
      SuppressibleMsgBox(
        '模型下载失败:' + #13#10 + GetExceptionMessage + #13#10#13#10 +
        '安装会继续完成,之后请在软件的"设置"页重新下载(支持断点续传)。',
        mbError, MB_OK, IDOK);
      Ok := False;
    end;
  finally
    DownloadPage.Hide;
  end;
  if not Ok then
    exit;

  // 从临时目录搬到正式位置
  DestDir := ModelDir('');
  ForceDirectories(DestDir);
  ForceDirectories(DestDir + '\tokenizer');
  TmpFile := ExpandConstant('{tmp}\');
  Log('安装模型文件到 ' + DestDir);
  CopyFile(TmpFile + 'model.bin', DestDir + '\model.bin', True);
  CopyFile(TmpFile + 'shared_vocabulary.txt', DestDir + '\shared_vocabulary.txt', True);
  CopyFile(TmpFile + 'config.json', DestDir + '\config.json', True);
  CopyFile(TmpFile + 'sentencepiece.bpe.model', DestDir + '\tokenizer\sentencepiece.bpe.model', True);
  CopyFile(TmpFile + 'tokenizer_config.json', DestDir + '\tokenizer\tokenizer_config.json', True);
  CopyFile(TmpFile + 'special_tokens_map.json', DestDir + '\tokenizer\special_tokens_map.json', True);
  CopyFile(TmpFile + 'tokenizer.json', DestDir + '\tokenizer\tokenizer.json', True);
end;
