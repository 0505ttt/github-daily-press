$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "请安装 Python 3.11 或更新版本。" }
}
& .venv\Scripts\python.exe -c "import gh_daily, bs4, requests, pypdf, tzdata"
if ($LASTEXITCODE -ne 0) {
    & .venv\Scripts\python.exe -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw "依赖安装失败，请检查网络后重试。" }
}
& .venv\Scripts\python.exe -m gh_daily serve --open
exit $LASTEXITCODE
