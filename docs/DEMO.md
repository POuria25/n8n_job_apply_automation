# Demo: what a session looks like

[Back to README](../README.md)

Text transcripts of the bot in Telegram, used in place of screenshots so that no employer or contact appears. **Every company, person, and address below is invented.** `[ … ]` marks an inline button.

Scenarios 1 to 3 are the output of the actual `Dialog` code from WF1, run on this invented input. The bot messages in scenarios 4 to 7 are copied from the message templates in the workflows. The `example.com` and `example.org` domains are placeholders: they do not accept mail, so a live run needs an address on a domain that does.

## 1. Guided entry

`/nouveau` asks for one field at a time. Address, postcode, and the HR contact are optional.

```text
You   /nouveau
Bot   🏢 Nom de l'entreprise ?

      (Tu peux aussi tout coller d'un coup : nom, email, adresse, RH… dans n'importe quel ordre.)
      [ ❌ Annuler ]

You   Société Exemple S.A.
Bot   📧 Email de l'entreprise ?
      [ ❌ Annuler ]

You   recrutement@example.com
Bot   📍 Adresse (rue et numéro) ?
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

You   12 rue de l'Exemple
Bot   📮 Code postal et localité ? (ex : L-9054 Ettelbruck)
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

You   L-1234 Ville
Bot   👤 As-tu le nom et l'email du responsable RH ?
      [ Oui ] [ Non ]
      [ ❌ Annuler ]

You   (taps Oui)
Bot   👤 Nom du responsable RH ? (ex : Madame Weber)
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

You   Madame Exemple
Bot   📧 Email du responsable RH ?
      [ ⏭️ Passer ]
      [ ❌ Annuler ]

You   rh@example.com
Bot   📋 Récapitulatif

      🏢 Société Exemple S.A.
      À l'attention de Madame Exemple
      📍 12 rue de l'Exemple, L-1234 Ville
      📧 Envoi à : recrutement@example.com
         + rh@example.com

      Enregistrer ?
      (Pour corriger, envoie simplement la bonne info.)
      [ ✅ Enregistrer ] [ ❌ Annuler ]

You   (taps ✅ Enregistrer)
Bot   ✅ Société Exemple S.A. enregistrée. La lettre arrive dans quelques minutes.

      Pour une autre entreprise : /nouveau
```

The recap is the place to catch a wrong pairing, such as one company's name with another company's email address. The bot cannot detect that; it sends to whatever is shown under "Envoi à".

## 2. Pasting everything at once

The same entry in a single message. Fields are recognised by their shape, in any order. The phone number is dropped: it never goes into the letter or the email.

```text
You   /new Société Exemple S.A.
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

## 3. Minimal entry

Only a name and an email. Without an HR contact the letter is addressed to the HR department.

```text
You   /nouveau
You   Garage Exemple
You   contact@example.org
You   (taps ⏭️ Passer)      address
You   (taps ⏭️ Passer)      postcode
You   (taps Non)            no HR contact
Bot   📋 Récapitulatif

      🏢 Garage Exemple
      À l'attention du service Ressources humaines
      📍 (pas d'adresse)
      📧 Envoi à : contact@example.org

      Enregistrer ?
      (Pour corriger, envoie simplement la bonne info.)
      [ ✅ Enregistrer ] [ ❌ Annuler ]
```

The bot's intermediate questions are the same as in scenario 1 and are left out here.

## 4. Bulk import

Any message containing a semicolon is read as bulk lines, one employer per line, with no `/nouveau` needed. Here the first line repeats the employer saved in scenario 1, the second is new, and the third has no valid email.

```text
You   Société Exemple S.A.; recrutement@example.com; 12 rue de l'Exemple; L-1234 Ville; Madame Exemple; rh@example.com
      Cabinet Exemple; contact@example.net
      Bureau Exemple; pas-une-adresse
Bot   ✅ 1 entreprise(s) ajoutée(s)
      ⚠️ 1 doublon(s) ignoré(s)
      ❌ Format invalide :
      Bureau Exemple; pas-une-adresse
```

A duplicate is an employer with the same name, or the same email domain, as one already saved for this applicant.

## 5. Preview, approval, sending

A few minutes after saving, the bot sends the compiled letter with the recipients and subject in the caption.

```text
Bot   📎 letter.pdf
      Société Exemple S.A. → recrutement@example.com + rh@example.com
      À l'attention de Madame Exemple
      12 rue de l'Exemple
      L-1234 Ville

      Objet : Candidature spontanée – Apprentissage DAP Agent administratif et commercial
      [ ✅ Envoyer ] [ 🔄 Refaire ] [ ❌ Ignorer ]

You   (taps ✅ Envoyer)
Bot   ✅ Validé : Société Exemple S.A. — envoi programmé.

      … at the next sending slot …

Bot   📤 Envoyé à Société Exemple S.A. (recrutement@example.com + rh@example.com)
```

Nothing is emailed until **Envoyer** is tapped. **Ignorer** answers `❌ Ignoré : Société Exemple S.A.` and **Refaire** answers `🔄 Nouvelle version en préparation : Société Exemple S.A.`

## 6. Domain that does not accept mail

If the MX check fails, no letter is drafted and the bot says why.

```text
Bot   ⚠️ Garage Exemple : le domaine example.org ne reçoit pas d'emails. Vérifie l'adresse et renvoie la ligne corrigée.
```

## 7. Tapping a button twice

A button only works while its application is waiting for approval. A second tap, or a tap on an old preview, changes nothing.

```text
You   (taps ✅ Envoyer again on the same preview)
Bot   ⚠️ Déjà traité ou introuvable.
```
