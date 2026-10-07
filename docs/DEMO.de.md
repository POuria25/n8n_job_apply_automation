# Demo: So sieht eine Sitzung aus

[Zurück zum README](../README.de.md) · [English](DEMO.md) · [Français](DEMO.fr.md) · **Deutsch** · [فارسی](DEMO.fa.md)

Textmitschriften des Bots in Telegram, anstelle von Screenshots, damit kein Arbeitgeber und kein Ansprechpartner erscheint. **Alle Firmen, Personen und Adressen unten sind erfunden.** `[ … ]` steht für eine Schaltfläche in der Nachricht.

Die Szenarien 1 bis 3 sind die Ausgabe des echten `Dialog`-Codes aus WF1, ausgeführt mit diesen erfundenen Eingaben. Die Bot-Nachrichten der Szenarien 4 bis 7 stammen aus den Nachrichtenvorlagen der Workflows; die Freigaberegel in Szenario 7 wurde geprüft, indem die Abfrage des Workflows gegen eine Testdatenbank lief. Die Domains `example.com` und `example.org` sind Platzhalter: Sie nehmen keine E-Mails an, ein echter Lauf braucht also eine Adresse auf einer Domain, die Mail empfängt.

## 1. Geführte Erfassung

`/nouveau` fragt ein Feld nach dem anderen ab. Anschrift, Postleitzahl und HR-Kontakt sind optional.

```text
Sie   /nouveau
Bot   🏢 Nom de l'entreprise ?

      (Tu peux aussi tout coller d'un coup : nom, email, adresse, RH… dans n'importe quel ordre.)
      [ ❌ Annuler ]

Sie   Société Exemple S.A.
Bot   📧 Email de l'entreprise ?
      [ ❌ Annuler ]

Sie   recrutement@example.com
Bot   📍 Adresse (rue et numéro) ?
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Sie   12 rue de l'Exemple
Bot   📮 Code postal et localité ? (ex : L-9054 Ettelbruck)
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Sie   L-1234 Ville
Bot   👤 As-tu le nom et l'email du responsable RH ?
      [ Oui ] [ Non ]
      [ ❌ Annuler ]

Sie   (Schaltfläche Oui)
Bot   👤 Nom du responsable RH ? (ex : Madame Weber)
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Sie   Madame Exemple
Bot   📧 Email du responsable RH ?
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

Sie   rh@example.com
Bot   📋 Récapitulatif

      🏢 Société Exemple S.A.
      À l'attention de Madame Exemple
      📍 12 rue de l'Exemple, L-1234 Ville
      📧 Envoi à : recrutement@example.com
         + rh@example.com

      Enregistrer ?
      (Pour corriger, envoie simplement la bonne info.)
      [ ✅ Enregistrer ] [ ❌ Annuler ]

Sie   (Schaltfläche ✅ Enregistrer)
Bot   ✅ Société Exemple S.A. enregistrée. La lettre arrive dans quelques minutes.

      Pour une autre entreprise : /nouveau
```

In der Zusammenfassung fällt eine falsche Kombination auf, etwa der Name einer Firma mit der E-Mail-Adresse einer anderen. Der Bot kann das nicht erkennen; er sendet an das, was unter „Envoi à“ steht.

## 2. Alles auf einmal einfügen

Dieselbe Erfassung in einer einzigen Nachricht. Die Felder werden an ihrer Form erkannt, in beliebiger Reihenfolge. Die Telefonnummer wird verworfen: Sie gelangt nie in das Anschreiben oder die E-Mail.

```text
Sie   /new Société Exemple S.A.
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

## 3. Minimale Erfassung

Nur ein Name und eine E-Mail-Adresse. Ohne HR-Kontakt wird das Anschreiben an die Personalabteilung adressiert.

```text
Sie   /nouveau
Sie   Garage Exemple
Sie   contact@example.org
Sie   (Schaltfläche ⏭️ Passer)      Anschrift
Sie   (Schaltfläche ⏭️ Passer)      Postleitzahl
Sie   (Schaltfläche Non)            kein HR-Kontakt
Bot   📋 Récapitulatif

      🏢 Garage Exemple
      À l'attention du service Ressources humaines
      📍 (pas d'adresse)
      📧 Envoi à : contact@example.org

      Enregistrer ?
      (Pour corriger, envoie simplement la bonne info.)
      [ ✅ Enregistrer ] [ ❌ Annuler ]
```

Die Zwischenfragen des Bots sind dieselben wie in Szenario 1 und werden hier ausgelassen.

## 4. Sammelimport

Jede Nachricht mit einem Semikolon wird als Importzeilen gelesen, ein Arbeitgeber pro Zeile, ohne `/nouveau`. Hier wiederholt die erste Zeile den in Szenario 1 gespeicherten Arbeitgeber, die zweite ist neu, und die dritte enthält keine gültige E-Mail-Adresse.

```text
Sie   Société Exemple S.A.; recrutement@example.com; 12 rue de l'Exemple; L-1234 Ville; Madame Exemple; rh@example.com
      Cabinet Exemple; contact@example.net
      Bureau Exemple; pas-une-adresse
Bot   ✅ 1 entreprise(s) ajoutée(s)
      ⚠️ 1 doublon(s) ignoré(s)
      ❌ Format invalide :
      Bureau Exemple; pas-une-adresse
```

Ein Duplikat ist ein Arbeitgeber mit demselben Namen oder derselben E-Mail-Domain wie ein bereits für diesen Bewerber gespeicherter.

## 5. Vorschau, Freigabe, Versand

Einige Minuten nach dem Speichern sendet der Bot das kompilierte Anschreiben, mit Empfängern und Betreff in der Bildunterschrift.

```text
Bot   📎 letter.pdf
      Société Exemple S.A. → recrutement@example.com + rh@example.com
      À l'attention de Madame Exemple
      12 rue de l'Exemple
      L-1234 Ville

      Objet : Candidature spontanée – Apprentissage DAP Agent administratif et commercial
      [ ✅ Envoyer ] [ 🔄 Refaire ] [ ❌ Ignorer ]

Sie   (Schaltfläche ✅ Envoyer)
Bot   ✅ Validé : Société Exemple S.A. — envoi programmé.

      … beim nächsten Versandtermin …

Bot   📤 Envoyé à Société Exemple S.A. (recrutement@example.com + rh@example.com)
```

Es wird nichts per E-Mail versendet, bevor **Envoyer** angetippt wurde. **Ignorer** antwortet `❌ Ignoré : Société Exemple S.A.` und **Refaire** antwortet `🔄 Nouvelle version en préparation : Société Exemple S.A.`

## 6. Domain, die keine E-Mails annimmt

Schlägt die MX-Prüfung fehl, wird kein Anschreiben erstellt, und der Bot nennt den Grund.

```text
Bot   ⚠️ Garage Exemple : le domaine example.org ne reçoit pas d'emails. Vérifie l'adresse et renvoie la ligne corrigée.
```

## 7. Alte Vorschauen und wiederholtes Antippen

Jede Schaltfläche gehört zu der Vorschau, mit der sie eingetroffen ist. Ein zweites Antippen ändert nichts, und nach **Refaire** funktionieren die Schaltflächen der früheren Vorschau nicht mehr: Nur die neueste Vorschau kann freigegeben werden.

```text
Sie   (Schaltfläche 🔄 Refaire in der ersten Vorschau)
Bot   🔄 Nouvelle version en préparation : Société Exemple S.A.

      … eine neue Vorschau trifft ein …

Sie   (Schaltfläche ✅ Envoyer in der ERSTEN Vorschau)
Bot   ⚠️ Déjà traité ou introuvable.

Sie   (Schaltfläche ✅ Envoyer in der neuen Vorschau)
Bot   ✅ Validé : Société Exemple S.A. — envoi programmé.
```
