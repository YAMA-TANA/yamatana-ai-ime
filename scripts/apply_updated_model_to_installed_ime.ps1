# PowerShell script to update installed Yamatana AI IME models and restart the AI ranker

$sourceDir = "c:\Users\lotof\Videos\research\live2d\yamatana-ai-ime\build\onnx-model-70m"
$targetDir = "C:\Program Files (x86)\Yamatana AI IME\ai_runtime\_internal\models\onnx"
$exePath = "C:\Program Files (x86)\Yamatana AI IME\ai_runtime\YamatanaAIIME.exe"

Write-Host "Stopping running YamatanaAIIME processes..." -ForegroundColor Cyan
Get-Process -Name "YamatanaAIIME" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

Write-Host "Copying updated ONNX models to $targetDir..." -ForegroundColor Cyan
Copy-Item "$sourceDir\ruri-ime-fp16.onnx" -Destination "$targetDir\ruri-ime-fp16.onnx" -Force
Copy-Item "$sourceDir\ruri-ime-int8.onnx" -Destination "$targetDir\ruri-ime-int8.onnx" -Force
Copy-Item "$sourceDir\tokenizer.json" -Destination "$targetDir\tokenizer.json" -Force

Write-Host "Files updated successfully:" -ForegroundColor Green
Get-ChildItem -Path $targetDir | Select-Object Name, Length, LastWriteTime | Format-Table

Write-Host "Restarting YamatanaAIIME..." -ForegroundColor Cyan
Start-Process -FilePath $exePath

Write-Host "Done!" -ForegroundColor Green
