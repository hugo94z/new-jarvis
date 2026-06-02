param(
    [Parameter(Mandatory=$true)]
    [string]$ImagePath
)

$ErrorActionPreference = 'Stop'

try {
    # Force output encoding to UTF-8 to prevent JSON parsing errors in Python
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    # Load Windows Runtime Assemblies
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    
    # Force loading of WinRT types
    $null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]

    # Helper to await WinRT async operations in PowerShell
    function Invoke-Async {
        param(
            [Parameter(Mandatory=$true)]
            $AsyncTask,
            [Parameter(Mandatory=$true)]
            [Type]$ResultType
        )
        $awaiter = [WindowsRuntimeSystemExtensions].GetMember('GetAwaiter', 'Method', 'Public,Static') | 
            Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
        $genericMethod = $awaiter.MakeGenericMethod($ResultType)
        return $genericMethod.Invoke($null, @($AsyncTask)).GetResult()
    }

    # Get absolute path
    $absolutePath = [System.IO.Path]::GetFullPath($ImagePath)
    if (-not (Test-Path $absolutePath)) {
        throw "Image file not found at: $absolutePath"
    }

    # Open image file using WinRT StorageFile
    $fileTask = [Windows.Storage.StorageFile]::GetFileFromPathAsync($absolutePath)
    $file = Invoke-Async -AsyncTask $fileTask -ResultType ([Windows.Storage.StorageFile])
            
    $streamTask = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    $stream = Invoke-Async -AsyncTask $streamTask -ResultType ([Windows.Storage.Streams.IRandomAccessStream])
              
    $decoderTask = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    $decoder = Invoke-Async -AsyncTask $decoderTask -ResultType ([Windows.Graphics.Imaging.BitmapDecoder])
               
    $softwareBitmapTask = $decoder.GetSoftwareBitmapAsync()
    $softwareBitmap = Invoke-Async -AsyncTask $softwareBitmapTask -ResultType ([Windows.Graphics.Imaging.SoftwareBitmap])

    # Initialize Windows OCR Engine (using user's preferred languages)
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($ocrEngine -eq $null) {
        # Fallback to English if user languages fail
        $lang = New-Object Windows.Globalization.Language("en-US")
        $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    }

    if ($ocrEngine -eq $null) {
        throw "Could not initialize Windows OCR Engine. Please check if OCR language pack is installed."
    }

    # Perform OCR
    $ocrResultTask = $ocrEngine.RecognizeAsync($softwareBitmap)
    $ocrResult = Invoke-Async -AsyncTask $ocrResultTask -ResultType ([Windows.Media.Ocr.OcrResult])

    # Structure the output results
    $linesData = New-Object System.Collections.Generic.List[System.Object]
    
    foreach ($line in $ocrResult.Lines) {
        $wordsData = New-Object System.Collections.Generic.List[System.Object]
        foreach ($word in $line.Words) {
            $wordsData.Add([PSCustomObject]@{
                text = $word.Text
                x = [int]$word.BoundingRect.X
                y = [int]$word.BoundingRect.Y
                width = [int]$word.BoundingRect.Width
                height = [int]$word.BoundingRect.Height
            })
        }
        $linesData.Add([PSCustomObject]@{
            text = $line.Text
            words = $wordsData
        })
    }

    $output = [PSCustomObject]@{
        success = $true
        text = $ocrResult.Text
        lines = $linesData
    }

    # Clean up WinRT objects to release file locks
    $softwareBitmap.Dispose()
    $stream.Dispose()

    # Output JSON representation
    $output | ConvertTo-Json -Depth 5 -Compress
}
catch {
    $errorOutput = [PSCustomObject]@{
        success = $false
        error = $_.Exception.Message
    }
    $errorOutput | ConvertTo-Json -Compress
    exit 1
}
