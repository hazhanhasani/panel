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
```

فایل‌های برنامه در `/opt/bluepanel` و داده‌های دائمی در `/var/lib/bluepanel` نگهداری می‌شوند.

آدرس پیش‌فرض پنل:

```text
http://SERVER_IP:8000/dashboard/
```

برای ساخت کلید راه‌اندازی Owner:

```bash
cd /opt/bluepanel
docker compose -p bluepanel exec bluepanel bluepanel-cli generate-temp-key
```

## به‌روزرسانی

دستور `bluepanel update` فقط کد را از مخزن زیر دریافت می‌کند:

```text
https://github.com/hazhanhasani/panel
```

سورس شاخه `main` به‌روزرسانی می‌شود، Docker image محلی دوباره ساخته می‌شود و سرویس BluePanel راه‌اندازی مجدد می‌شود. نصب و آپدیت به اسکریپت یا Docker image پروژه بالادستی وابسته نیست.

بررسی نسخه جدید پنل نیز از Releaseهای همین مخزن انجام می‌شود و بررسی نسخه Node از `hazhanhasani/node` انجام می‌گیرد.

## مجوز

BluePanel بر پایه یک پروژه متن‌باز توسعه یافته و فایل مجوز و اعلان‌های قانونی موردنیاز مجوز اصلی حفظ می‌شوند. نام تجاری، مسیر نصب، Releaseها و منبع آپدیت BluePanel مستقل هستند.
