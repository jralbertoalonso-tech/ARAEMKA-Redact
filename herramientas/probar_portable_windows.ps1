$ErrorActionPreference = "Stop"

$raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$carpeta = Join-Path $raiz "dist\AnoniPRO"
$ejecutable = Join-Path $carpeta "AnoniPRO.exe"
$puerto = 8765
$url = "http://127.0.0.1:$puerto"
$temporal = Join-Path $env:TEMP "anonipro-smoke"

if (-not (Test-Path $ejecutable)) {
    throw "No existe $ejecutable"
}

New-Item -ItemType Directory -Force -Path $temporal | Out-Null
$imagen = Join-Path $temporal "ocr-prueba.png"
$respuesta = Join-Path $temporal "respuesta.json"

Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 1200, 220
$grafico = [System.Drawing.Graphics]::FromImage($bmp)
$grafico.Clear([System.Drawing.Color]::White)
$fuente = New-Object System.Drawing.Font("Arial", 28)
$grafico.DrawString(
    "Paciente: Pedro Armas Gonzalez. DNI: 12345678Z. Telephone: 628 11 22 33.",
    $fuente,
    [System.Drawing.Brushes]::Black,
    20,
    65
)
$bmp.Save($imagen, [System.Drawing.Imaging.ImageFormat]::Png)
$fuente.Dispose()
$grafico.Dispose()
$bmp.Dispose()

$env:ANONIPRO_PUERTO = "$puerto"
$env:ANONIPRO_NO_ABRIR_NAVEGADOR = "1"
$proceso = Start-Process -FilePath $ejecutable -WorkingDirectory $carpeta -PassThru

try {
    $estado = $null
    for ($i = 0; $i -lt 180; $i++) {
        Start-Sleep -Seconds 1
        if ($proceso.HasExited) {
            throw "AnoniPRO terminó durante el arranque (código $($proceso.ExitCode))."
        }
        try {
            $estado = Invoke-RestMethod -Uri "$url/api/estado" -TimeoutSec 2
            break
        }
        catch {
            # El primer arranque carga los modelos de lenguaje y puede tardar.
        }
    }
    if ($null -eq $estado) {
        throw "AnoniPRO no respondió en 180 segundos."
    }
    if (-not $estado.ocr_disponible -or -not $estado.ocr_espanol -or -not $estado.ocr_ingles) {
        throw "El ejecutable arrancó, pero no detectó el OCR español e inglés incluido."
    }

    & curl.exe --silent --show-error --fail `
        --form "archivo=@$imagen" `
        --form "categorias=[]" `
        --form "lista_personalizada=[]" `
        --form "lista_blanca=[]" `
        "$url/api/documentos" --output $respuesta
    if ($LASTEXITCODE -ne 0) {
        throw "La prueba de subida y OCR devolvió el código $LASTEXITCODE."
    }
    $resultado = Get-Content -Raw -Path $respuesta | ConvertFrom-Json
    if (-not $resultado.por_ocr) {
        throw "La imagen de prueba se procesó, pero no quedó marcada como OCR."
    }

    Write-Host "OK: el ejecutable arranca, responde y procesa una imagen con OCR."
}
finally {
    if ($null -ne $proceso -and -not $proceso.HasExited) {
        Stop-Process -Id $proceso.Id -Force
        $proceso.WaitForExit()
    }
    Remove-Item -Force -ErrorAction SilentlyContinue $imagen, $respuesta
}
