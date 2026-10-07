<div dir="rtl">

# نمونه: یک جلسه چه شکلی دارد

[بازگشت به README](../README.fa.md) · [English](DEMO.md) · [Français](DEMO.fr.md) · [Deutsch](DEMO.de.md) · **فارسی**

رونوشت متنیِ کار ربات در تلگرام، به جای تصویر صفحه، تا نام هیچ کارفرما یا مخاطبی دیده نشود. **همهٔ شرکت‌ها، افراد و نشانی‌های زیر ساختگی هستند.** نشانهٔ `[ … ]` یعنی یک دکمه در پیام.

در رونوشت‌ها `You` یعنی شما، `Bot` یعنی ربات و `(taps …)` یعنی دکمه‌ای را لمس می‌کنید. متن پیام‌های ربات به زبان فرانسوی است.

سناریوهای ۱ تا ۳ خروجیِ کدِ واقعی `Dialog` در WF1 هستند که روی همین ورودی ساختگی اجرا شده است. پیام‌های ربات در سناریوهای ۴ تا ۷ از قالب پیام‌های گردش‌کارها برداشته شده‌اند؛ قاعدهٔ تأیید در سناریوی ۷ با اجرای پرس‌وجوی گردش‌کار روی یک پایگاه دادهٔ آزمایشی بررسی شده است. دامنه‌های `example.com` و `example.org` فقط نمونه‌اند: ایمیل نمی‌پذیرند، پس اجرای واقعی به نشانی‌ای روی دامنه‌ای نیاز دارد که ایمیل دریافت می‌کند.

## ۱. ثبت گام‌به‌گام

دستور `/nouveau` هر بار یک مورد را می‌پرسد. نشانی، کد پستی و مخاطب منابع انسانی اختیاری هستند.

</div>

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

<div dir="rtl">

خلاصه جایی است که می‌توان جفت‌شدن نادرست را دید، مثلاً نام یک شرکت با نشانی ایمیل شرکتی دیگر. ربات نمی‌تواند این را تشخیص دهد؛ به هر نشانی‌ای که زیر «Envoi à» آمده می‌فرستد.

## ۲. چسباندن همه‌چیز یک‌جا

همان ثبت در یک پیام. موارد از روی شکلشان شناخته می‌شوند، به هر ترتیبی که باشند. شمارهٔ تلفن کنار گذاشته می‌شود: هرگز وارد نامه یا ایمیل نمی‌شود.

</div>

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

<div dir="rtl">

## ۳. ثبت حداقلی

فقط یک نام و یک نشانی ایمیل. بدون مخاطب منابع انسانی، نامه خطاب به واحد منابع انسانی نوشته می‌شود.

</div>

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

<div dir="rtl">

پرسش‌های میانیِ ربات همان پرسش‌های سناریوی ۱ هستند و اینجا نیامده‌اند.

## ۴. ورود گروهی

هر پیامی که نقطه‌ویرگول داشته باشد به صورت سطرهای ورود گروهی خوانده می‌شود، هر سطر یک کارفرما، بدون نیاز به `/nouveau`. اینجا سطر اول همان کارفرمای ذخیره‌شده در سناریوی ۱ است، سطر دوم جدید است و سطر سوم نشانی ایمیل معتبر ندارد.

</div>

```text
You   Société Exemple S.A.; recrutement@example.com; 12 rue de l'Exemple; L-1234 Ville; Madame Exemple; rh@example.com
      Cabinet Exemple; contact@example.net
      Bureau Exemple; pas-une-adresse
Bot   ✅ 1 entreprise(s) ajoutée(s)
      ⚠️ 1 doublon(s) ignoré(s)
      ❌ Format invalide :
      Bureau Exemple; pas-une-adresse
```

<div dir="rtl">

تکراری یعنی کارفرمایی که نام یا دامنهٔ ایمیلش با کارفرمایی که پیش‌تر برای همین متقاضی ذخیره شده یکی است.

## ۵. پیش‌نمایش، تأیید، ارسال

چند دقیقه پس از ذخیره، ربات نامهٔ ساخته‌شده را می‌فرستد و گیرندگان و موضوع را در زیرنویس می‌آورد.

</div>

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

<div dir="rtl">

تا وقتی **Envoyer** لمس نشود هیچ ایمیلی فرستاده نمی‌شود. **Ignorer** پاسخ می‌دهد `❌ Ignoré : Société Exemple S.A.` و **Refaire** پاسخ می‌دهد `🔄 Nouvelle version en préparation : Société Exemple S.A.`

## ۶. دامنه‌ای که ایمیل نمی‌پذیرد

اگر بررسی MX ناموفق باشد، نامه‌ای ساخته نمی‌شود و ربات دلیل را می‌گوید.

</div>

```text
Bot   ⚠️ Garage Exemple : le domaine example.org ne reçoit pas d'emails. Vérifie l'adresse et renvoie la ligne corrigée.
```

<div dir="rtl">

## ۷. پیش‌نمایش‌های قدیمی و لمس دوباره

هر دکمه به همان پیش‌نمایشی وابسته است که همراهش رسیده است. لمس دوباره چیزی را تغییر نمی‌دهد، و پس از **Refaire** دکمه‌های پیش‌نمایش قبلی از کار می‌افتند: فقط جدیدترین پیش‌نمایش را می‌توان تأیید کرد.

</div>

```text
You   (taps 🔄 Refaire on the first preview)
Bot   🔄 Nouvelle version en préparation : Société Exemple S.A.

      … a new preview arrives …

You   (taps ✅ Envoyer on the FIRST preview)
Bot   ⚠️ Déjà traité ou introuvable.

You   (taps ✅ Envoyer on the new preview)
Bot   ✅ Validé : Société Exemple S.A. — envoi programmé.
```
