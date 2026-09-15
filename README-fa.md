# BluePanel — بلوپنل

BluePanel یک پنل مستقل برای مدیریت سرویس‌های مبتنی بر Xray، کاربران، اشتراک‌ها، نودها، محدودیت حجم و زمان و آمار مصرف است.

این مخزن منبع اصلی نصب، ساخت و به‌روزرسانی BluePanel است.

## نصب سریع

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/hazhanhasani/panel/main/install.sh)" @ install
```

دستورات مدیریت:

```bash
bluepanel status
bluepanel logs
bluepanel update
bluepanel restart
bluepanel version
```

فایل‌های برنامه در `/opt/bluepanel` و داده‌های دائمی در `/var/lib/bluepanel` نگهداری می‌شوند.

آدرس پیش‌فرض پنل:

```text
http://SERVER_IP:8000/dashboard/
```

برای ساخت کلید موقت یک‌بارمصرف و ایجاد حساب Owner:

```bash
bluepanel generate-temp-key
# یا اجرای مستقیم هر فرمان CLI داخلی:
bluepanel cli generate-temp-key
```

## فعال‌سازی SSL بعد از نصب

ابتدا رکورد A/AAAA دامنه را به IP سرور متصل و ورودی TCP پورت 80 را باز کنید. سپس، بعد از اینکه پنل با HTTP بالا آمد، اجرا کنید:

```bash
bluepanel ssl panel.example.com admin@example.com
```

این فرمان با acme.sh از Let's Encrypt گواهی می‌گیرد، تمدید خودکار را تنظیم می‌کند، مسیر گواهی‌ها را در `/opt/bluepanel/.env` ثبت می‌کند و پنل را با HTTPS بازراه‌اندازی می‌کند. داده‌های گواهی در `/var/lib/bluepanel/certs` باقی می‌مانند.

## به‌روزرسانی

دستور `bluepanel update` فقط کد را از مخزن زیر دریافت می‌کند:

```text
https://github.com/hazhanhasani/panel
```

سورس شاخه `main` به آخرین commit رسمی به‌روزرسانی می‌شود، Docker image محلی دوباره ساخته می‌شود، مهاجرت‌های دیتابیس اجرا می‌شوند و سرویس BluePanel راه‌اندازی مجدد می‌شود. پیش از آپدیت از SQLite و image فعلی نسخهٔ بازگشت نگه داشته می‌شود. نسخه و commit نصب‌شده را با `bluepanel version` ببینید.

بررسی نسخه جدید پنل نیز از Releaseهای همین مخزن انجام می‌شود و بررسی نسخه Node از `hazhanhasani/node` انجام می‌گیرد.

## مجوز

BluePanel بر پایه یک پروژه متن‌باز توسعه یافته و فایل مجوز و اعلان‌های قانونی موردنیاز مجوز اصلی حفظ می‌شوند. نام تجاری، مسیر نصب، Releaseها و منبع آپدیت BluePanel مستقل هستند.

