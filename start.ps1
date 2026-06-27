$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "首次运行：正在创建环境并安装依赖..." -ForegroundColor Cyan
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
}

$port = 8501
while ($true) {
    try {
        $listener = [System.Net.Sockets.TcpListener]::new(
            [System.Net.IPAddress]::Loopback,
            $port
        )
        $listener.Start()
        $listener.Stop()
        break
    }
    catch {
        $port += 1
    }
}

Write-Host "正在启动 家装经营洞察 Agent..." -ForegroundColor Green
Write-Host "打开地址：http://localhost:$port" -ForegroundColor Cyan
.venv\Scripts\python.exe -m streamlit run app.py --server.port $port
