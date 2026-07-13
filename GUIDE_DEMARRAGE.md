# 🚀 GUIDE DE DÉMARRAGE RAPIDE - CHARTIST-BOT

**Benjamin, voici comment démarrer ton bot en 15 minutes!**

---

## ⚡ ÉTAPE 1: Installation (5 min)

### 1.1 Cloner le projet
```bash
cd /chemin/vers/ton/dossier
git clone <repo-url>
cd CHARTIST-BOT
```

### 1.2 Créer l'environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 1.3 Installer les dépendances
```bash
pip install -r requirements.txt
```

**Ça devrait prendre 2-3 minutes max.**

---

## 🔑 ÉTAPE 2: Obtenir tes Credentials (5 min)

### 2.1 Deriv API Token
1. Aller sur: https://app.deriv.com/account/api-token
2. Cliquer sur "Create new token"
3. Nommer: `chartist-bot`
4. Sélectionner permissions: ✅ Trade, ✅ Admin
5. **Copier le token (ça ne s'affichera qu'une fois!)**
6. Noter aussi ton **App ID** (visible en haut)

### 2.2 Telegram Bot Token
1. Ouvrir Telegram et chercher `@BotFather`
2. Envoyer: `/newbot`
3. Donner le nom: `ChartistBot` (ou ce que tu veux)
4. Donner le username: `chartist_bot_<random>` (doit être unique)
5. **Copier le token reçu**

### 2.3 Telegram Chat ID
1. Envoyer un message à ton bot (n'importe lequel)
2. Aller sur: https://api.telegram.org/bot<TON_TOKEN>/getUpdates
3. Remplacer `<TON_TOKEN>` par le token du bot
4. **Copier le `chat_id` dans la réponse**

---

## 📝 ÉTAPE 3: Configuration (3 min)

### 3.1 Créer le fichier .env
```bash
cp .env.example .env
```

### 3.2 Éditer .env avec tes credentials
```bash
nano .env  # ou ouvre avec l'éditeur de ton choix
```

Remplir:
```env
DERIV_APP_ID=TON_APP_ID
DERIV_API_TOKEN=TON_TOKEN_DERIV
TELEGRAM_BOT_TOKEN=TON_TOKEN_TELEGRAM
TELEGRAM_CHAT_ID=TON_CHAT_ID_TELEGRAM
```

**Sauvegarde et quitte.**

### 3.3 (Optionnel) Personnaliser config.json

Éditer `config.json` si tu veux ajuster:
```json
{
  "trading": {
    "risk_per_trade_percent": 1.5,    // Risque par trade (1.5%)
    "max_daily_loss_percent": 5.0      // Perte max/jour (5%)
  },
  "confirmation": {
    "multi_timeframe": true,           // Multi-TF confirmation
    "pullback_required": true,         // Pullback confirmation
    "atr_multiplier": 1.5              // ATR factor
  }
}
```

**Les defaults sont déjà optimisés, tu peux laisser comme ça!**

---

## ▶️ ÉTAPE 4: Démarrer le Bot (2 min)

### 4.1 Lancer
```bash
python main.py
```

### 4.2 Vérifier que tout fonctionne
Tu devrais voir:
```
[15:32:05] ✓ Configuration chargée
[15:32:06] ✓ Bot initialisé
[15:32:07] ✓ Connecté à Deriv
[15:32:08] ✓ Authentification réussie
[15:32:09] ✓ Abonné à 10 paires
[15:32:10] ℹ️  Bot connecté et prêt à trader
```

**Si tu vois ça = BON! Le bot est prêt! 🎉**

---

## 📊 ÉTAPE 5: Vérifier que tu reçois les Alertes

### Test d'alerte Telegram
1. Vérifier que tu as reçu le message `Bot connecté et prêt à trader` sur Telegram
2. Si oui ✅ tout fonctionne!
3. Si non ❌ vérifier:
   - Chat ID correct?
   - Token Telegram correct?
   - T'as envoyé un message au bot avant?

---

## 🎯 C'est PARTI!

Maintenant le bot:
- ✅ Écoute les 10 paires en M5 et M15
- ✅ Détecte automatiquement les patterns
- ✅ Confirme avec multi-timeframe
- ✅ Envoie les signaux sur Telegram
- ✅ Ouvre les trades automatiquement
- ✅ Gère le risque (1.5% max par trade)
- ✅ Ferme au TP ou SL automatiquement

---

## 📈 Que faire maintenant?

### Option 1: Regarder en live
```bash
tail -f logs/chartist_*.log
```
*Affiche les logs en direct*

### Option 2: Arrêter le bot
```bash
Ctrl+C
```

### Option 3: Tester d'abord avec le backtester
*(À venir - phase backtesting)*

---

## ⚙️ Configuration Fine (Optionnel)

### Changer le risque par trade
Dans `config.json`:
```json
"trading": {
  "risk_per_trade_percent": 2.0  // Passer à 2% au lieu de 1.5%
}
```

### Ajouter/Retirer des paires
Dans `config.json`:
```json
"trading": {
  "pairs": [
    "BOOM1000",        // Garder les bonnes
    "BOOM300",
    "XAUUSD",
    "VOLATILITY100",
    // Ajouter d'autres paires ici
  ]
}
```

### Réduire les alertes Telegram
Dans `config.json`:
```json
"alerts": {
  "alert_on_pattern_detection": false,  // Pas d'alerte pattern détecté
  "alert_on_trade_entry": true,         // Garder alerte entrée
  "alert_on_trade_exit": true           // Garder alerte sortie
}
```

---

## 🔍 Comprendre les Logs

```
[Timestamp] [Niveau] Message

Niveaux:
ℹ️  INFO     = Information importante
⚠️  WARNING  = Avertissement, vérifier
❌ ERROR    = Erreur, bot peut arrêter
📌 DEBUG    = Détail technique (ignorable)
```

Exemples:
```
[09:15:30] ✓ Bot initialisé                    = OK
[09:16:45] 🎯 Head & Shoulders détecté         = Pattern trouvé!
[09:16:47] ✓ Confirmation Multi-TF: OK         = Signal confirmé!
[09:16:48] 📈 Trade ouvert #a3f8k9             = Trade ouvert!
[09:17:30] 📊 Trade fermé [TAKE PROFIT]        = Trade gagné! 🎉
[09:17:31] PnL: +150.00 USD (+2.1%)
```

---

## 🆘 Problèmes Courants

### "Erreur: Connexion Deriv refusée"
```
✅ Solution:
1. Vérifier les credentials dans .env
2. Vérifier la connexion internet
3. Relancer: python main.py
```

### "Pas d'alerte Telegram"
```
✅ Solution:
1. Vérifier que Chat ID est correct
2. Envoyer un message à @<ton_bot>
3. Relancer le bot
```

### "Pas de signaux détectés"
```
✅ Solution:
1. Attendre 10-15 min (besoin de candlesticks)
2. Vérifier les paires sont actives
3. Réduire sensitivity dans config.json
```

---

## 💡 TIPS PRO

1. **Toujours tester avec 1.5% de risque** d'abord
2. **Regarder les patterns** sur le graphique Deriv pour vérifier
3. **Surveiller 1 heure** pour voir si ça détecte les patterns
4. **Vérifier les stats** quotidiennement dans les logs
5. **Ne JAMAIS modifier le code** en live (stop d'abord)

---

## 📞 Besoin d'Aide?

1. Vérifier les logs: `tail logs/chartist_*.log`
2. Vérifier la config: `cat config.json`
3. Vérifier .env: `cat .env` (pas de secrets dedans!)
4. Me contacter: Je t'aiderai!

---

## 🎉 FIN!

**Ton bot est maintenant:**
- ✅ Installé
- ✅ Configuré
- ✅ Connecté à Deriv
- ✅ Connecté à Telegram
- ✅ Prêt à trader!

**Bon trading! 🚀**

---

**Questions à poser maintenant:**
- Sensibilité des patterns OK?
- Besoin d'ajuster le risque?
- Besoin de plus de paires?

Je suis là pour ça! 💪
