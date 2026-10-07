# Démonstration : à quoi ressemble une session

[Retour au README](../README.fr.md) · [English](DEMO.md) · **Français** · [Deutsch](DEMO.de.md) · [فارسی](DEMO.fa.md)

Transcriptions textuelles du bot dans Telegram, utilisées à la place de captures d'écran pour qu'aucun employeur ni contact n'apparaisse. **Toutes les entreprises, personnes et adresses ci-dessous sont inventées.** `[ … ]` désigne un bouton intégré au message.

Les scénarios 1 à 3 sont la sortie du véritable code `Dialog` de WF1, exécuté sur ces données inventées. Les messages du bot des scénarios 4 à 7 sont repris des modèles de messages des workflows ; la règle de validation du scénario 7 a été vérifiée en exécutant la requête du workflow sur une base de test. Les domaines `example.com` et `example.org` sont des exemples : ils n'acceptent pas de courrier, donc un essai réel exige une adresse sur un domaine qui en reçoit.

## 1. Saisie guidée

`/nouveau` demande un champ à la fois. L'adresse, le code postal et le contact RH sont facultatifs.

```text
Vous  /nouveau
Bot   🏢 Nom de l'entreprise ?

      (Tu peux aussi tout coller d'un coup : nom, email, adresse, RH… dans n'importe quel ordre.)
      [ ❌ Annuler ]

Vous  Société Exemple S.A.
Bot   📧 Email de l'entreprise ?
      [ ❌ Annuler ]

Vous  recrutement@example.com
Bot   📍 Adresse (rue et numéro) ?
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Vous  12 rue de l'Exemple
Bot   📮 Code postal et localité ? (ex : L-9054 Ettelbruck)
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Vous  L-1234 Ville
Bot   👤 As-tu le nom et l'email du responsable RH ?
      [ Oui ] [ Non ]
      [ ❌ Annuler ]

Vous  (bouton Oui)
Bot   👤 Nom du responsable RH ? (ex : Madame Weber)
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Vous  Madame Exemple
Bot   📧 Email du responsable RH ?
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Vous  rh@example.com
Bot   📋 Récapitulatif

      🏢 Société Exemple S.A.
      À l'attention de Madame Exemple
      📍 12 rue de l'Exemple, L-1234 Ville
      📧 Envoi à : recrutement@example.com
         + rh@example.com

      Enregistrer ?
      (Pour corriger, envoie simplement la bonne info.)
      [ ✅ Enregistrer ] [ ❌ Annuler ]

Vous  (bouton ✅ Enregistrer)
Bot   ✅ Société Exemple S.A. enregistrée. La lettre arrive dans quelques minutes.

      Pour une autre entreprise : /nouveau
```

Le récapitulatif est l'endroit où repérer une mauvaise association, par exemple le nom d'une entreprise avec l'adresse e-mail d'une autre. Le bot ne peut pas la détecter ; il envoie à ce qui est affiché sous « Envoi à ».

## 2. Tout coller d'un coup

La même saisie en un seul message. Les champs sont reconnus à leur forme, dans n'importe quel ordre. Le numéro de téléphone est écarté : il ne figure jamais dans la lettre ni dans l'e-mail.

```text
Vous  /new Société Exemple S.A.
      recrutement@example.com
      12 rue de l'Exemple
      L-1234 Ville
      +352 12 34 56
      /hr Madame Exemple
      rh@example.com
Bot   ✔️ Noté : entreprise, email entreprise, adresse, code postal, contact RH, email RH
      (ignoré : +352 12 34 56)

      📋 Récapitulatif

      🏢 Société Exemple S.A.
      À l'attention de Madame Exemple
      📍 12 rue de l'Exemple, L-1234 Ville
      📧 Envoi à : recrutement@example.com
         + rh@example.com

      Enregistrer ?
      (Pour corriger, envoie simplement la bonne info.)
      [ ✅ Enregistrer ] [ ❌ Annuler ]
```

## 3. Saisie minimale

Seulement un nom et une adresse e-mail. Sans contact RH, la lettre est adressée au service des ressources humaines.

```text
Vous  /nouveau
Vous  Garage Exemple
Vous  contact@example.org
Vous  (bouton ⏭️ Passer)      adresse
Vous  (bouton ⏭️ Passer)      code postal
Vous  (bouton Non)            pas de contact RH
Bot   📋 Récapitulatif

      🏢 Garage Exemple
      À l'attention du service Ressources humaines
      📍 (pas d'adresse)
      📧 Envoi à : contact@example.org

      Enregistrer ?
      (Pour corriger, envoie simplement la bonne info.)
      [ ✅ Enregistrer ] [ ❌ Annuler ]
```

Les questions intermédiaires du bot sont les mêmes qu'au scénario 1 et ne sont pas reprises ici.

## 4. Import en masse

Tout message contenant un point-virgule est lu comme des lignes d'import, un employeur par ligne, sans `/nouveau`. Ici, la première ligne répète l'employeur enregistré au scénario 1, la deuxième est nouvelle et la troisième n'a pas d'adresse e-mail valide.

```text
Vous  Société Exemple S.A.; recrutement@example.com; 12 rue de l'Exemple; L-1234 Ville; Madame Exemple; rh@example.com
      Cabinet Exemple; contact@example.net
      Bureau Exemple; pas-une-adresse
Bot   ✅ 1 entreprise(s) ajoutée(s)
      ⚠️ 1 doublon(s) ignoré(s)
      ❌ Format invalide :
      Bureau Exemple; pas-une-adresse
```

Un doublon est un employeur portant le même nom, ou ayant le même domaine e-mail, qu'un employeur déjà enregistré pour ce candidat.

## 5. Aperçu, validation, envoi

Quelques minutes après l'enregistrement, le bot envoie la lettre compilée, avec les destinataires et l'objet en légende.

```text
Bot   📎 letter.pdf
      Société Exemple S.A. → recrutement@example.com + rh@example.com
      À l'attention de Madame Exemple
      12 rue de l'Exemple
      L-1234 Ville

      Objet : Candidature spontanée – Apprentissage DAP Agent administratif et commercial
      [ ✅ Envoyer ] [ 🔄 Refaire ] [ ❌ Ignorer ]

Vous  (bouton ✅ Envoyer)
Bot   ✅ Validé : Société Exemple S.A. — envoi programmé.

      … au prochain créneau d'envoi …

Bot   📤 Envoyé à Société Exemple S.A. (recrutement@example.com + rh@example.com)
```

Rien n'est envoyé par e-mail tant que **Envoyer** n'a pas été touché. **Ignorer** répond `❌ Ignoré : Société Exemple S.A.` et **Refaire** répond `🔄 Nouvelle version en préparation : Société Exemple S.A.`

## 6. Domaine qui n'accepte pas de courrier

Si la vérification MX échoue, aucune lettre n'est rédigée et le bot explique pourquoi.

```text
Bot   ⚠️ Garage Exemple : le domaine example.org ne reçoit pas d'emails. Vérifie l'adresse et renvoie la ligne corrigée.
```

## 7. Anciens aperçus et appuis répétés

Chaque bouton est lié à l'aperçu avec lequel il est arrivé. Un deuxième appui ne change rien, et après **Refaire** les boutons de l'aperçu précédent cessent de fonctionner : seul l'aperçu le plus récent peut être validé.

```text
Vous  (bouton 🔄 Refaire sur le premier aperçu)
Bot   🔄 Nouvelle version en préparation : Société Exemple S.A.

      … un nouvel aperçu arrive …

Vous  (bouton ✅ Envoyer sur le PREMIER aperçu)
Bot   ⚠️ Déjà traité ou introuvable.

Vous  (bouton ✅ Envoyer sur le nouvel aperçu)
Bot   ✅ Validé : Société Exemple S.A. — envoi programmé.
```
