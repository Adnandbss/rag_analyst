# Script PowerShell pour push vers GitHub
# Exécutez ce fichier depuis le dossier rag_analyst

Write-Host "🚀 Configuration GitHub pour RAG-Analyst" -ForegroundColor Green
Write-Host ""

# Vérifier si on est dans le bon dossier
if (!(Test-Path "app")) {
    Write-Host "❌ Erreur : Ce script doit être exécuté depuis le dossier rag_analyst" -ForegroundColor Red
    exit 1
}

Write-Host "📝 Étape 1: Demander votre username GitHub..." -ForegroundColor Yellow
$username = Read-Host "Entrez votre username GitHub"

if ([string]::IsNullOrWhiteSpace($username)) {
    Write-Host "❌ Username invalide" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📝 Étape 2: Ajout du remote GitHub..." -ForegroundColor Yellow
$repoUrl = "https://github.com/$username/rag-analyst.git"

# Vérifier si le remote existe déjà
$existingRemote = git remote -v 2>$null
if ($existingRemote -and $existingRemote -match "origin") {
    Write-Host "⚠️  Le remote 'origin' existe déjà" -ForegroundColor Yellow
    $overwrite = Read-Host "Voulez-vous le remplacer ? (o/n)"
    if ($overwrite -eq "o" -or $overwrite -eq "O") {
        git remote remove origin
        git remote add origin $repoUrl
        Write-Host "✅ Remote mis à jour" -ForegroundColor Green
    } else {
        Write-Host "⏭️  Remote conservé" -ForegroundColor Yellow
    }
} else {
    git remote add origin $repoUrl
    Write-Host "✅ Remote 'origin' ajouté : $repoUrl" -ForegroundColor Green
}

Write-Host ""
Write-Host "📝 Étape 3: Push vers GitHub..." -ForegroundColor Yellow
Write-Host "URL de votre repository: $repoUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Lancement du push..." -ForegroundColor Green
Write-Host ""

# Push vers master
git push -u origin master

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ SUCCÈS ! Votre code est maintenant sur GitHub 🎉" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Votre repository: https://github.com/$username/rag-analyst" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📥 Pour récupérer sur votre autre PC:" -ForegroundColor Yellow
    Write-Host "   git clone https://github.com/$username/rag-analyst.git" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "❌ Erreur lors du push" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Solutions possibles:" -ForegroundColor Yellow
    Write-Host "1. Créez d'abord le repository sur GitHub.com" -ForegroundColor White
    Write-Host "2. Vérifiez que vous avez les droits d'accès" -ForegroundColor White
    Write-Host "3. Vérifiez votre authentification GitHub" -ForegroundColor White
}
