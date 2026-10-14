$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Get-Content (Join-Path $root ".env") | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $name, $value = $_.Split('=', 2)
    Set-Item -Path "Env:$name" -Value $value
}

$homePath = Join-Path $env:LOCALAPPDATA "grafana-oss"
$server = Join-Path $homePath "bin\grafana.exe"
if (-not (Test-Path $server)) {
    throw "Grafana is not installed at $server"
}

& $server server --homepath $homePath --config (Join-Path $root "grafana\custom.ini")
