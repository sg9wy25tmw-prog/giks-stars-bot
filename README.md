
# بوت متجر نجوم تيليجرام ⭐

## محتويات الحزمة
- bot.py                 -> كود البوت الرئيسي
- config.txt             -> ملف يحتوي التوكن (موجود بالفعل)
- requirements.txt       -> المكتبات المطلوبة
- Procfile               -> لتشغيل على Heroku
- shop.db                -> قاعدة بيانات (تُنشأ تلقائياً عند التشغيل)
- 65CB...jpg             -> صورة البوت (مسار محلي مُضمن)

## تشغيل محلي (Linux / VPS / Termux)
1. تأكد من وجود Python 3.
2. ثبت المتطلبات:
   ```
   pip install -r requirements.txt
   ```
3. ضع التوكن في ملف `config.txt` (هو موجود فعلاً: `text.txt` تم نسخه).
4. شغّل:
   ```
   python3 bot.py
   ```

## نشر على Heroku
1. أنشئ تطبيق جديد في Heroku.
2. ادفع الكود (Git) أو ارفعه كـ ZIP.
3. ضع CONFIG VARS إذا أردت (بدلاً من config.txt) — `TOKEN`.
4. شغّل worker من Procfile.

## كيف البوت يتعامل مع المدفوعات (Stars)
- البوت يدير "رصيد نجوم" داخليًا.
- **لتفعيل المدفوعات الحقيقية:** استعمل Telegram Payments أو قابل للدفع عبر مزود، ثم نفّذ حدث الدفع وادعُ الدالة `credit_cmd` أو أضف السطر لزيادة stars للمستخدم.
- أو بخلاصة: المستخدم يرسل انتاج الدفع لمالك البوت، والمالك يضيف النجوم يدوياً عبر:
  ```
  /credit @username amount
  ```

## أوامر مهمة
- للمستخدمين:
  - /start
  - /listservices
  - /buy <service_id> [qty]
  - /mybalance
  - /topup
- للمالك:
  - /addservice name | desc | price | [auto:0/1]
  - /delservice <id>
  - /orders
  - /fulfill <order_id>
  - /credit @username amount
  - /vip_add @username days

## ملاحظة أمان
- توخّى الحذر مع `config.txt` — لا تنشر التوكن علناً.
