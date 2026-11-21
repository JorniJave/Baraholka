# Скрипт для проверки статуса бота
Write-Host "🔍 Проверка статуса бота..." -ForegroundColor Cyan

# Проверка запущенных процессов Python
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "✅ Бот запущен!" -ForegroundColor Green
    Write-Host "📊 Найдено процессов Python: $($pythonProcesses.Count)" -ForegroundColor Yellow
    $pythonProcesses | ForEach-Object {
        Write-Host "   - Процесс ID: $($_.Id), Память: $([math]::Round($_.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor White
    }
    
    # Проверка логов
    if (Test-Path "baraholka.log") {
        Write-Host "`n📝 Последние строки из логов:" -ForegroundColor Cyan
        Get-Content "baraholka.log" -Tail 10 | ForEach-Object {
            Write-Host "   $_" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "❌ Бот не запущен!" -ForegroundColor Red
    Write-Host "💡 Запустите бота командой: .\start_bot.ps1" -ForegroundColor Yellow
}

# Проверка файла .env
if (Test-Path ".env") {
    Write-Host "`n✅ Файл .env найден" -ForegroundColor Green
} else {
    Write-Host "`n❌ Файл .env не найден!" -ForegroundColor Red
}

# Проверка базы данных
if (Test-Path "baraholka.db") {
    $dbSize = (Get-Item "baraholka.db").Length
    Write-Host "✅ База данных найдена (размер: $([math]::Round($dbSize / 1KB, 2)) KB)" -ForegroundColor Green
} else {
    Write-Host "⚠️  База данных не найдена (будет создана при первом запуске)" -ForegroundColor Yellow
}


