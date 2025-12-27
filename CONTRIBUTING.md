# Guide de Contribution - Nexus Trade

Merci de votre intérêt pour contribuer à Nexus Trade ! 🎉

## Comment Contribuer

### Signaler des Bugs

Si vous trouvez un bug, merci de créer une issue avec:
- Description claire du problème
- Étapes pour reproduire
- Comportement attendu vs comportement actuel
- Version de Go, Python, et OS
- Logs pertinents

### Proposer des Fonctionnalités

Pour proposer une nouvelle fonctionnalité:
1. Créez une issue décrivant la fonctionnalité
2. Expliquez le cas d'usage
3. Attendez les retours avant de commencer à coder

### Pull Requests

1. **Fork** le projet
2. **Créez une branche** pour votre fonctionnalité:
   ```bash
   git checkout -b feature/ma-super-fonctionnalité
   ```
3. **Commitez** vos changements:
   ```bash
   git commit -m "Ajout: ma super fonctionnalité"
   ```
4. **Push** vers votre fork:
   ```bash
   git push origin feature/ma-super-fonctionnalité
   ```
5. **Ouvrez une Pull Request**

## Standards de Code

### Go

- Utilisez `gofmt` pour formater le code
- Suivez les conventions Go standards
- Ajoutez des tests pour toute nouvelle fonctionnalité
- Commentez les fonctions publiques
- Gardez les fonctions courtes et focalisées

### Python

- Suivez PEP 8
- Utilisez des type hints quand possible
- Documentez les fonctions avec docstrings
- Ajoutez des tests unitaires

### Commits

Format de message de commit:
```
Type: Description courte (50 caractères max)

Description détaillée si nécessaire (72 caractères par ligne)

Fixes #123
```

Types:
- `Ajout:` Nouvelle fonctionnalité
- `Fix:` Correction de bug
- `Refactor:` Refactorisation de code
- `Docs:` Documentation
- `Test:` Ajout/modification de tests
- `Style:` Formatage, pas de changement de code
- `Perf:` Amélioration de performance

## Tests

Avant de soumettre une PR:

```bash
# Tests Go
go test ./...

# Tests Python
pytest ai/

# Lint
make lint
```

## Structure du Projet

```
nexus-trade/
├── cmd/            # Point d'entrée
├── internal/       # Code interne
│   ├── analyzer/   # Module IA
│   ├── blockchain/ # Module blockchain
│   ├── database/   # Module DB
│   ├── trader/     # Module trading
│   └── web/        # Module web
├── ai/             # Scripts Python IA
└── web/            # Frontend
```

## Questions ?

N'hésitez pas à:
- Ouvrir une issue pour discussion
- Rejoindre nos discussions GitHub
- Consulter la documentation

Merci de contribuer à Nexus Trade ! 🚀
