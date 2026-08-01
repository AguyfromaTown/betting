[CmdletBinding()]
param(
    [ValidatePattern('^$|^\d{4}-\d{2}-\d{2}$')]
    [string]$Date = '',

    [ValidateRange(1.01, 1000.0)]
    [double]$OddsMin = 1.5,

    [ValidateRange(1.01, 1000.0)]
    [double]$OddsMax = 1.6,

    [ValidateRange(0.01, 1000000000.0)]
    [double]$VirtualBankroll = 100.0,

    [switch]$Force
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$botPath = Join-Path $projectRoot 'tennis-bot\tennis_bot.py'
$requirementsPath = Join-Path $projectRoot 'tennis-bot\requirements-test.txt'
$virtualEnvironment = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $virtualEnvironment 'Scripts\python.exe'
$promptedOddsKey = $false
$previousOddsKey = $env:ODDS_API_KEY

if ($OddsMin -gt $OddsMax) {
    throw 'OddsMin must be less than or equal to OddsMax.'
}

if (-not (Test-Path -LiteralPath $botPath) -or -not (Test-Path -LiteralPath $requirementsPath)) {
    throw "Run-paper files are incomplete under $projectRoot."
}

try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $systemPython = Get-Command python -ErrorAction SilentlyContinue
        if (-not $systemPython) {
            throw 'Python 3.11 or newer is required and must be available as python in PATH.'
        }
        Write-Host 'Creating isolated .venv environment...'
        & $systemPython.Source -m venv $virtualEnvironment
        if ($LASTEXITCODE -ne 0) {
            throw 'Unable to create the Python virtual environment.'
        }
    }

    Write-Host 'Installing/updating project dependencies in .venv...'
    & $venvPython -m pip install --disable-pip-version-check --requirement $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Dependency installation failed; paper trading was not started.'
    }

    Write-Host 'Running the complete test and coverage gate...'
    & $venvPython -m coverage run -m unittest discover -s (Join-Path $projectRoot 'tennis-bot') -p 'test_*.py'
    if ($LASTEXITCODE -ne 0) {
        throw 'Tests failed; paper trading was not started.'
    }
    & $venvPython -m coverage report --fail-under=70
    if ($LASTEXITCODE -ne 0) {
        throw 'Coverage is below 70%; paper trading was not started.'
    }

    $oddsKeyNames = 'ODDS_API_KEY', 'ODDS_API_KEY_2', 'ODDS_API_KEY_3', 'ODDS_API_KEY_4', 'ODDS_API_KEY_5'
    $hasOddsKey = $false
    foreach ($keyName in $oddsKeyNames) {
        if ([Environment]::GetEnvironmentVariable($keyName)) {
            $hasOddsKey = $true
            break
        }
    }
    if (-not $hasOddsKey) {
        $secureKey = Read-Host 'Enter one Odds API key for this paper run (input is hidden and not saved)' -AsSecureString
        $plainKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw 'An Odds API key is required; paper trading was not started.'
        }
        $env:ODDS_API_KEY = $plainKey
        $plainKey = $null
        $promptedOddsKey = $true
    }

    $arguments = @(
        $botPath,
        '--paper-trading',
        '--bankroll', ([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0:0.00}', $VirtualBankroll)),
        '--odds-min', ([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0:0.00}', $OddsMin)),
        '--odds-max', ([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0:0.00}', $OddsMax))
    )
    if ($Date) {
        $arguments += '--date', $Date
    }
    if ($Force) {
        $arguments += '--force'
    }

    Write-Host "Starting isolated paper run with virtual bankroll EUR $($VirtualBankroll.ToString('0.00'))..."
    & $venvPython @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "The tennis paper run failed with exit code $LASTEXITCODE."
    }
}
finally {
    if ($promptedOddsKey) {
        if ($null -eq $previousOddsKey) {
            Remove-Item Env:ODDS_API_KEY -ErrorAction SilentlyContinue
        }
        else {
            $env:ODDS_API_KEY = $previousOddsKey
        }
    }
}
