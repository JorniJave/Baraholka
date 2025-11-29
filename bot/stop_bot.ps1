# Скрипт для остановки всех запущенных экземпляров бота
Write-Host "🔍 Поиск запущенных процессов Python..." -ForegroundColor Yellow

$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "🛑 Найдено процессов Python: $($pythonProcesses.Count)" -ForegroundColor Red
    $pythonProcesses | ForEach-Object {
        Write-Host "   Останавливаю процесс ID: $($_.Id)" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "✅ Все процессы Python остановлены" -ForegroundColor Green
} else {
    Write-Host "✅ Запущенных процессов Python не найдено" -ForegroundColor Green
}

Write-Host "`n💡 Теперь можно запустить бота командой: python bot.py" -ForegroundColor Cyan

