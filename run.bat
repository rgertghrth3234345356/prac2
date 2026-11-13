@echo off
cd /d "%~dp0"

if "%~1"=="" (
    py -m src.main --package A --repository test-repository.json --test-mode --ascii --order
) else (
    py -m src.main %*
)

echo.
echo Program finished.
pause
