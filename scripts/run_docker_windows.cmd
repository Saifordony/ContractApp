@echo off
setlocal

cd /d "%~dp0.."

if not exist "docker-compose.yml" (
  echo [ERROR] Could not find docker-compose.yml. Make sure you are in repo root.
  exit /b 1
)

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/
  exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker daemon is not running.
  echo [INFO] Please open Docker Desktop and wait until it says Running, then rerun this script.
  exit /b 1
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
)


REM Clean up legacy fixed-name containers from older compose versions
for %%C in (contract_analysis_backend contract_analysis_mongo) do (
  docker rm -f %%C >nul 2>nul
)

echo [INFO] Starting services with docker compose...
docker compose up --build --remove-orphans

endlocal
