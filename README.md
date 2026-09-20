Net Monitor Pro
Net Monitor Pro هو برنامج خفيف لمراقبة الشبكة على نظام Windows، تم تطويره باستخدام Python وواجهة Tkinter الرسومية.

يوفر البرنامج واجهة بسيطة لعرض ومراقبة معلومات الشبكة واستخدام موارد النظام.

المميزات
مراقبة نشاط الشبكة.

عرض معلومات اتصالات الشبكة.

مراقبة استخدام موارد النظام.

واجهة رسومية بسيطة وسهلة الاستخدام.

نسخة جاهزة للعمل بصيغة .exe.

لا يحتاج تثبيت Python عند استخدام النسخة التنفيذية.

التحميل
يمكن تحميل أحدث نسخة من البرنامج من صفحة Releases:

تحميل Net Monitor Pro

النسخة الجاهزة لنظام Windows هي:

NetMonitorPro.exe

طريقة التشغيل
تشغيل النسخة الجاهزة EXE
ادخل إلى صفحة Releases.

حمّل ملف NetMonitorPro.exe.

بعد اكتمال التحميل، شغّل الملف بالنقر المزدوج عليه.

سيبدأ البرنامج مباشرة.

لا تحتاج إلى تثبيت Python لتشغيل نسخة .exe.

تشغيل المشروع من المصدر
إذا كنت تريد تشغيل البرنامج باستخدام ملفات المصدر، يجب تثبيت Python أولًا.

بعد ذلك افتح موجه الأوامر داخل مجلد المشروع ونفّذ:

pip install psutil

ثم شغّل البرنامج:

python net_monitor.py

المتطلبات
لتشغيل البرنامج من المصدر
Windows

Python 3.x

مكتبة psutil

Tkinter

لتشغيل نسخة EXE
Windows

لا تحتاج إلى تثبيت Python أو المكتبات المطلوبة بشكل منفصل.

إنشاء نسخة EXE
إذا أردت إنشاء نسخة تنفيذية جديدة من المشروع باستخدام PyInstaller، نفّذ:

pip install pyinstaller psutil

ثم:

python -m PyInstaller --onefile --noconsole --name NetMonitorPro net_monitor.py

بعد انتهاء العملية ستجد البرنامج داخل:

dist\NetMonitorPro.exe

هيكل المشروع
Net-Monitor-Pro/
├── net_monitor.py
├── NetMonitorPro.spec
├── Net_Monitor_README.txt
├── .gitignore
└── README.md
