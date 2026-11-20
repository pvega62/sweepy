                                  ████  █   █  ████  ████  ████  █   █
                                  █     █   █  █     █     █  █  █   █
                                  ████  █ █ █  ███   ███   ████   █ █ 
                                    █  ██ ██  █     █     █       █  
                                  ████  █   █  ████  ████  █       █  
<h1 align="center">Sweepy: بحث وتقييم الوظائف بمحركات متعددة</h1>

<p align="center">
  <strong>ابحث بذكاء أكبر، وأفضل، وأسرع، وأقوى.</strong><br>
  كشط متوازٍ للوظائف عبر أفضل المنصات، وتقييم آلي للسيرة الذاتية، وتقارير مرتبة.
</p>

<p align="center">
  <a href="https://github.com/pvega62/sweepy/actions"><img src="https://github.com/pvega62/sweepy/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10 أو أحدث"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="رخصة MIT"></a>
  <a href="https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme"><img src="https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271" alt="تقييم M8ven"></a>
</p>

<p align="center">
  <a href="#quick-start"><strong>البدء السريع</strong></a> ·
  <a href="#features">الميزات</a> ·
  <a href="#job-engines">محركات الوظائف</a> ·
  <a href="#portfolio-support">دعم ملف الأعمال</a> ·
  <a href="#documentation">التوثيق</a> ·
  <a href="https://github.com/pvega62/sweepy/issues/new">أبلغ عن مشكلة</a>
</p>

---

Sweepy أداة مجانية تبحث في لوحات الوظائف وتقيّم كل إعلان مقابل سيرتك الذاتية. تقرأ مواقع التوظيف لدى الشركات ولوحات الوظائف، وتحذف الإعلانات المكررة والمنتهية، ثم تكتب تقريرًا مرتبًا. يمكنك إيقاف فحص التكرار لجولة واحدة دون تغيير ملفك الشخصي. يفتح معالج الإعداد لوحة انطلاق للبحث وإعداد الملف الشخصي وضبط البحث ومهام صندوق أدوات Sweepy مثل إدارة المحركات والمجمّعات.

> راجع **[CHANGELOG.md](CHANGELOG.md)** لمعرفة الإصدار الحالي وسجل الإصدارات.

## <a name="features"></a>الميزات

- **يبحث في أماكن كثيرة في وقت واحد.** يجمع الإعلانات من Greenhouse وAshby وLever وWorkable وBuilt In New York City وLinkedIn وIndeed وGlassdoor وZipRecruiter. يعمل كل من هذه المصادر دون مفتاح API.
- **يشغّل كل محرك بالتوازي.** تبدأ المحركات المفعّلة معًا. تستغرق الجولة بعد ذلك زمن أبطأ محرك تقريبًا بدلًا من مجموع أزمنتها.
- **يواصل العمل عند فشل لوحة.** يحصل كل محرك على مهلة زمنية وقاطع دائرة. لا تستطيع نقطة نهاية واحدة فاشلة أن تعطّل الجولة أو أن تكرر الطلب نفسه خمس مرات.
- **يضيف محركات أخرى عند الحاجة.** ثبّت HireHunt أو openroles أو jobdrop أو Apify من المعالج دون مغادرة الطرفية.
- **يقيّم كل إعلان مقابل سيرتك الذاتية.** يقرأ نص سيرتك الذاتية بصيغة PDF أو Word ويقيس مقدار مطابقته للإعلان.
- **يستبعد الروابط المنتهية.** يفحص كل عنوان URL ويزيل الإعلانات التي لم تعد موجودة.
- **يفحص الإعلانات المكررة عبر اللوحات.** يطابق عنوان الوظيفة والشركة والموقع بعد التطبيع، حتى عندما تستخدم اللوحات عناوين URL مختلفة. مرّر `--no-dedupe` للاحتفاظ بإعلان كل لوحة في جولة واحدة.
- **يتخطى الإعلانات التي رأيتها.** تعرض الجولة اليومية أدوارًا جديدة بدلًا من قائمة الأمس. يخفي Sweepy الإعلانات المعروضة مدة أربعة أيام. مرّر `--include-seen` لإعادتها في جولة واحدة.
- **يوجّهك إلى السيرة الذاتية المناسبة.** يرسل كل وظيفة إلى مسار السيرة الذاتية الذي كتبته لذلك الدور، ثم يضع على البطاقة شارة ملوّنة.
- **يجعل ملف أعمالك جزءًا من كل قرار.** وجّه Sweepy إلى ملف أعمال على الإنترنت أو ملف محلي بصيغة PDF أو Word أو Markdown أو نص أو HTML. تسرد كل بطاقة أعمال ذلك الملف. وعندما تتقدم لأكثر من نوع واحد من الأدوار، احتفظ بملف أعمال لكل مسار سيرة ذاتية.
- **ينشئ تقريرًا يمكنك استخدامه.** ينتج ملف PDF ببطاقة واحدة لكل صفحة مع روابط قابلة للنقر، إضافة إلى ملفات CSV وJSON لتتبعك الخاص.
- **يحوّل ملف CSV إلى متتبع للتقديمات.** ينتهي ملف CSV بالأعمدة `date_applied` و`status` و`interview_stage` و`offer_amount` و`offer_date` و`follow_up_date` و`contact` و`notes`. املأها عبر Excel أو Google Sheets أو Notion. ينسخ Sweepy مدخلاتك إلى الجولات اللاحقة من الملف الشخصي نفسه. يمنحك ملف PDF قائمة قراءة واحدة مرتبة مع روابط التقديم على كل بطاقة. ويحتفظ جدول البيانات بالأدوار التي تتجاوز حد بطاقات PDF ويسجل ما فعلته بشأن كل دور. أوقف الأعمدة بـ `export.tracking: false`.

## <a name="quick-start"></a>البدء السريع

تحتاج إلى **Python 3.10 أو أحدث**. في Python 3.13، تُبنى بعض الحزم من المصدر. قد تحتاج إلى Microsoft C++ Build Tools أولًا. راجع [تثبيت Sweepy](https://pvega62.github.io/software/docs/sweepy/installation).

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

يثبّت `pip install -e .` كل تبعية أساسية ويسجل الأمر `sweepy` في مجلد Python Scripts. أعد فتح الطرفية مرة واحدة حتى يلتقط الصدف ذلك المجلد من PATH. شغّل `sweepy` لبدء المعالج، أو أضف خيار أمر مثل `sweepy --run`. ويمكنك أيضًا تشغيل السكربت مباشرة بـ `python swee.py`.

يمنحك ذلك الأمر الواحد المحركين المدمجين. ويعرض المعالج المحركات الأربعة الاختيارية عند حاجتك إليها، ولا تشغّل ملف متطلبات منفصلًا أبدًا.

لجلب كل محرك متوافق مسبقًا بدلًا من ذلك، أضف علامة واحدة إلى الأمر نفسه:

```bash
pip install -e ".[all-engines]"
```

يضيف ذلك HireHunt وopenroles وApify في حل واحد. ويبقى `jobdrop` خارجًا لأن بياناته الوصفية لا تُحل بجوار JobSpy. ثبّته بـ `sweepy --install-engines jobdrop --allow-engine-conflicts` عندما تريد لوحاته الـ33. ويغطي قسم [محركات الوظائف](#job-engines) المسارين.

يفتح تشغيل `sweepy` لوحة انطلاق المعالج المبنية على المربعات. استخدم مفاتيح الأسهم للتنقل بين **بدء جولة**، و**بناء ملف شخصي**، و**تحميل ملف شخصي**، و**إعدادات الجولة**، و**صندوق أدوات Sweepy**، و**الخروج من Sweepy**، ثم اضغط Enter. وتذكر العناوين الفرعية للمربعات الإجراء بكلمات واضحة، كما في **شغّل بحثك عن الوظائف الآن** أو **افتح بحثًا حفظته**. ويتيح لك **تحميل ملف شخصي** اختيار ملف محفوظ لاستخدامه في الجولة التالية. ويحتوي صندوق الأدوات على تحرير الملف الشخصي وإدارة المحركات وتسجيل التصحيح والمساعدة والسجلات الأخيرة وتحويل المستندات والتحديثات. ويجمع **بناء ملف شخصي** اسمك ومسميات الوظائف المستهدفة والموقع ومسار السيرة الذاتية. ويحفظ المعالج الملف الشخصي عند الانتهاء. شغّل `sweepy --setup --profile profiles/your_profile.yaml` لتحرير ملف شخصي مباشرة.

تُفتح القوائم الفرعية بـ **← رجوع**، الذي يعيدك إلى القائمة التي فتحتها. ويفعل Esc الشيء نفسه. وعند سؤال، يعيد Esc فتح الإجابة السابقة. وداخل قائمة فرعية، يصعد Esc مستوى واحدًا. وفي لوحة الانطلاق، يخرج Esc. وينهي Ctrl+C من أي مكان.

لجلب تعليمات برمجية جديدة عند صدور إصدار، شغّل:

```bash
sweepy --update
```

يفحص Sweepy مستودع Git البعيد لديك ويدفع نسخة العمل للأمام. ويعيد تثبيت `requirements.txt` وأي محركات اختيارية ثبّتها بالفعل. ويرفض تعديل نسخة عمل فيها تغييرات غير مثبّتة. وفضّل `sweepy --check-update` لفحص إصدار جديد دون تغيير أي شيء.

ثم شغّل جولتك الأولى:

```bash
sweepy --run
```

تجري `--run` جولة بالملف الشخصي الأخير الذي حفظته. ولتسمية ملف شخصي آخر، استخدم `sweepy --profile profiles/your_profile.yaml`.

أوقف فحص التكرار لجولة واحدة دون تحرير إعداد في الملف الشخصي:

```bash
sweepy --run --no-dedupe
sweepy --profile profiles/your_profile.yaml --no-dedupe
```

افتراضيًا، يحتفظ Sweepy بإعلان واحد عندما تسرد لوحات مختلفة العنوان والشركة والموقع المطبع نفسه. وتقبل أداة `run_sweep` في بروتوكول سياق النموذج (MCP) القيمة `deduplicate=false` للتجاوز نفسه في كل جولة.

ويخفي Sweepy أيضًا الإعلانات من الجولات السابقة. راجعها مرة أخرى أو ابدأ من جديد:

```bash
sweepy --run --include-seen      # report earlier postings too
sweepy --run --reset-history     # forget them, then sweep
sweepy --reset-history           # forget the last profile's history and exit
```

ابنِ ملفًا شخصيًا أو حدّثه دون مطالبات عندما تكتب سكربتًا لـ Sweepy:

```bash
sweepy --setup --non-interactive \
  --name "Alex Rivera" \
  --titles "Technical Writer,UX Writer" \
  --location "New York, NY" \
  --resume C:/resumes/alex.pdf \
  --sources jobspy,openroles \
  --openroles-companies figma,stripe,notion \
  --timeout 120 --no-cache
```

يتحقق Sweepy من المحركات المفعّلة قبل كتابة الملف. ويفشل الحقل المطلوب الناقص سريعًا مع ذكر السبب. وفي المعالج التفاعلي، اترك معرّفات شركات OpenRoles فارغة لتخطي ذلك المحرك. ويبحث OpenRoles في لوحات الشركات المسمّاة فقط. وتحتاج الملفات الشخصية غير التفاعلية التي تفعّل OpenRoles مع ذلك إلى `--openroles-companies`. وتغطي العلامات غير التفاعلية `--sources` و`--jobspy-sites` و`--hirehunt-sources` و`--jobdrop-sites` و`--openroles-companies` و`--apify-actor` و`--timeout` و`--cache-ttl` و`--no-cache` و`--history-days` و`--no-history` و`--job-tracking` / `--no-job-tracking`.

املأ ملفًا شخصيًا عندما تفضّل محررًا على المطالبات واستدعاءات الأدوات:

```bash
cp profiles/template_custom.yaml profiles/my_search.yaml
# replace the four REQUIRED values, then run the copy
sweepy --profile profiles/my_search.yaml
```

يوثّق القالب كل إعداد مع قيمته الافتراضية. ويطبع Sweepy اسمك ومسمياتك وموقعك قبل بدء الاكتشاف. ويظهر أي خطأ إملائي في أول سطر من المخرجات.

حوّل ملف سيرة ذاتية أو ملاحظات إلى PDF دون فتح المعالج:

```bash
sweepy --convert path/to/resume.docx
```

يقبل `--convert` ملفات `.docx` و`.doc` و`.txt` و`.md` و`.pdf`. ويكتب ملف PDF بجوار الملف الأصلي ويطبع المسار النهائي.

تستغرق الجولة من 30 إلى 90 ثانية. ويطبع Sweepy تقدمه أثناء العمل:

1. **يحمّل ملفك الشخصي.**
2. **يكتشف الوظائف الشاغرة** عبر المنصات التي فعّلتها.
3. **يتحقق من الروابط** ويسقط المنتهية منها.
4. **يقيّم كل دور** مقابل سيرتك الذاتية.
5. **يكتب تقريرك.**

## <a name="what-you-get"></a>ما تحصل عليه

تكتب كل جولة ملفات تحمل ختم التاريخ في مجلد `results/`. وتبقى التقارير السابقة في مكانها. وتضيف الجولة التي تُنفَّذ عبر MCP الكلمة `mcp` إلى اسم الملف، كما في `paralegal_nyc_mcp_2026-10-27-223115.pdf`. ويتبع الختم ساعة جهازك. اضبط `export.timezone` لتسمية الملفات بمنطقة زمنية أخرى.

- **تقرير PDF.** بطاقة واحدة لكل دور، مرتبة حسب درجة المطابقة، مع الأجر والمزايا ورابط للتقديم.
- **ملف CSV.** كل حقل في البطاقة، ونص الإعلان كاملًا، وثمانية أعمدة لتتبع الوظائف ينسخها Sweepy إلى الجولات اللاحقة. افتحه في Excel أو Google Sheets أو Notion. واضبط `export.description_chars` على رقم موجب عندما تريد ملفات أصغر. وينتهي النص المقتطع بملاحظة تعدّ الأحرف المحذوفة.
- **ملف JSON.** البيانات نفسها بصيغة تستطيع أدوات أخرى قراءتها.

افتح [ملف PDF النموذجي](docs/sample_report.pdf)، أو اعرض [الصفحة 1 كصورة](docs/sample_report.png).

## <a name="job-engines"></a>محركات الوظائف

يتضمن Sweepy محركين ويمكنه تنزيل أربعة أخرى. ويعمل كل محرك خلف المحوّل نفسه. وتبدو الملفات الشخصية نفسها أيًّا كان المحرك الذي وجد الإعلان.

| المحرك | التوفر | ما يكشطه | الخوادم الوسيطة | User-Agent | الأوصاف |
|---|---|---|---|---|---|
| `jobspy` | مدمج | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | نعم | نعم | تبديل |
| `ats` | مدمج | Greenhouse, Ashby, Lever, Workable, Built In NYC | لا | لا | دائمًا |
| `hirehunt` | تنزيل | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop، وست لوحات شركات (Google Careers, Amazon, Meta, Apple, Netflix, Microsoft) | لا | لا | دائمًا |
| `openroles` | تنزيل | لوحات Greenhouse, Lever, Ashby, Workday التي تسميها | لا | لا | دائمًا |
| `jobdrop` | تنزيل | 33 لوحة تشمل Google, Wellfound, Workday, iCIMS, Dice, USAJobs | نعم | نعم | تبديل |
| `apify` | تنزيل | ممثلون مُدارون، LinkedIn افتراضيًا | يتولاه الممثل | يتولاه الممثل | يعتمد على الممثل |

يبلّغ `jobdrop` عن تعارض في البيانات الوصفية مع JobSpy: فهو يثبّت `curl-cffi<0.8`، بينما يتطلب JobSpy الإصدار `curl_cffi>=0.16.2`. وقيد الإصدار هذا قديم. ويعمل `jobdrop` جيدًا على المكتبة الأحدث، التي تتضمن مع ذلك كل ملف انتحال يستخدمه (`safari17_2_ios`، `chrome120`، `chrome124`).

ويفشل تثبيت `pip install` العادي لكليهما مع ذلك. ويستبعد `--install-engines all` المحرك `jobdrop`. أضف `--allow-engine-conflicts` لتثبيته بالطريقة المدعومة. يثبّت Sweepy المحرك `jobdrop` بـ `--no-deps`، ثم يحل متطلباته الأخرى، فيبقى `curl_cffi` على إصدار JobSpy ويعمل المحركان.

```bash
sweepy --install-engines all
sweepy --install-engines openroles,apify
sweepy --install-engines jobdrop --allow-engine-conflicts
```

يبلّغ `pip check` مع ذلك عن الحد الأعلى القديم للمحرك `jobdrop` بعد ذلك التثبيت. ويصف التحذير البيانات الوصفية، لا التعليمات البرمجية العاملة.

أو افتح المعالج واختر **صندوق أدوات Sweepy** ثم **تنزيل محركات الوظائف**. تسرد تلك الشاشة لوحات كل محرك وحالة تثبيته. ويسأل قبل تشغيل `pip`. وإذا اخترت محركًا ناقصًا أثناء بناء ملف شخصي، عرض المعالج التنزيل نفسه. ولا يشغّل Sweepy تثبيتًا دون تأكيدك.

### <a name="disk-footprint"></a>البصمة على القرص

مقيسة على Windows مع Python 3.13:

| التثبيت | الحزم على القرص | ملاحظات |
|---|---|---|
| النواة (`requirements.txt`) | 283 MB | 53 حزمة، تشمل pandas وpymupdf وMCP SDK |
| `hirehunt` | +13 MB | يضيف rich وmarkdown-it-py |
| `openroles` | +0.3 MB | مكتبة Python القياسية فقط |
| `apify-client` | +14 MB | يضيف impit وmore-itertools |
| `jobdrop` | +406 MB | يتصدرها scipy (134 MB)، وplaywright (113 MB)، وtls-client (93 MB)، وselenium (34 MB) |

ويستهلك التثبيت الكامل للمحركات المتوافقة نحو **320 MB**. ويصل الإجمالي بإضافة `jobdrop` إلى نحو **725 MB** قبل تنزيل متصفح.

تعيش ملفات المتصفح التنفيذية خارج بيئة Python وتصل عند أول استخدام:

- نسخة Chromium من Playwright تبلغ نحو **710 MB** (Chromium مع غلافه بلا واجهة).
- مجموعة Playwright الكاملة، بما فيها Firefox وWebKit، تبلغ نحو **1.2 GB**.
- ينزّل Camoufox، الذي يستخدمه `jobdrop` في مسار التخفي، نسخة Firefox معدّلة عند أول تشغيل.

يشغّل Sweepy كل محرك مدمج دون متصفح. ولا يحتاج التثبيت الأساسي إلى شيء من هذه المساحة.

اسرد المحركات وحالة تثبيتها في أي وقت:

```bash
sweepy --list-engines
```

يقرأ `openroles` اللوحات التي تسميها ويشترط معرّفات الشركات. ويقرأ `apify` متغير البيئة `APIFY_TOKEN` ويحتسب التكلفة على حساب Apify الخاص بك.

تثبيت محرك لا يفعّله. أضفه إلى ملف شخصي بإحدى ثلاث طرق:

1. **المعالج.** شغّل `sweepy`، واختر **صندوق أدوات Sweepy**، ثم **إدارة محركات الوظائف**، ثم **اختر المحركات والإعدادات**. تعرض المحركات المثبّتة وسم `[installed]`. حدّد محركًا فيطالبك المعالج بإعداداته.
2. **تحرير الملف الشخصي.** حمّل الملف الشخصي، ثم اختر **إدارة محركات الوظائف** من شاشة المراجعة.
3. **سطر الأوامر.** سمِّ المحرك في `--sources` وقدّم إعداداته:

```bash
sweepy --setup --non-interactive --profile profiles/your_profile.yaml \
  --sources jobspy,ats,jobdrop --jobdrop-sites linkedin,indeed,wellfound
```

تتحقق كل طريقة من إعدادات المحرك قبل كتابة الملف. وتفشل القيمة الناقصة، مثل معرّفات شركات `openroles`، مع ذكر السبب بدلًا من حفظ ملف شخصي معطوب.

### <a name="choosing-boards"></a>اختيار اللوحات

تسرد خطوة المنصات في معالج الملف الشخصي كل لوحة يستطيع Sweepy البحث فيها، مجمّعة تحت المحرك الذي يقرأها. تظهر اللوحات الـ63 كلها في مكان واحد بدلًا من الخمس المدمجة فقط.

| المجموعة | اللوحات | الوسم |
|---|---|---|
| `jobspy` (8) | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | `built in` |
| `ats` (5) | Greenhouse, Ashby, Lever, Workable, Built In NYC | `built in` |
| `hirehunt` (12) | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, Google Careers, Amazon, Meta, Apple, Netflix, Microsoft | `needs download` حتى التثبيت |
| `openroles` (4) | Greenhouse, Lever, Ashby, Workday | `needs download`، ويحتاج معرّفات شركات |
| `jobdrop` (33) | Google, Wellfound, Workday, iCIMS, Dice, USAJobs, Handshake، والمزيد | `needs download`، ويتعارض مع JobSpy |
| `apify` (1) | LinkedIn عبر ممثل Apify | `needs download`، ويحتاج `APIFY_TOKEN` |

يعرض كل صف محركه وحالة تثبيته، مثل `Indeed  [jobspy · built in]` أو `Wellfound  [jobdrop · needs download]`. وترى الوسم قبل أن تلتزم بالاختيار. وإذا حدّدت لوحة من محرك بلا تثبيت محلي، طبع المعالج الأمر الذي يثبّته. ويعرض المحرك المثبّت `installed` بدلًا من ذلك. وإعادة فتح ملف شخصي محفوظ تعرض لوحاته الحالية محددة مسبقًا. ويحتفظ Sweepy بلوحة من محرك غير مثبّت في الملف الشخصي، وتتخطى الجولة ذلك المحرك مع تحذير حتى ينتهي التثبيت.

### <a name="engine-settings"></a>إعدادات المحرك

```yaml
sources:
  enabled: [jobspy, ats, openroles]
  greenhouse:
    discovery: broad
    concurrency: 20
  openroles:
    ats: [greenhouse, lever, ashby, workday]
    companies: [figma, stripe, notion]
  jobdrop:
    sites: [linkedin, indeed, google, glassdoor]
    headless: true
    fetch_descriptions: true
    proxies: ["user:pass@host:port"]
cache:
  enabled: true
  ttl_seconds: 3600
history:
  enabled: true
  retention_days: 4
  match: url+role
  path: null
orchestrator:
  timeout_per_source_seconds: 180
  circuit_breaker:
    failure_threshold: 5
    cooldown_seconds: 30
```

تظل الملفات الشخصية الأقدم تعمل. وما تزال القيم المنطقية لللوحات تحت `sources.jobspy` تفعّل لوحات JobSpy الفردية وتوقفها. وأي ملف شخصي بلا قائمة `sources.enabled` يعود افتراضيًا إلى JobSpy مع قارئات ATS المدمجة.

- **تبقى الأوصاف مفعّلة افتراضيًا.** يطابق التقييم نص الإعلان مع سيرتك الذاتية. أوقف `fetch_descriptions` فقط إذا قبلت مطابقات أضعف مقابل جولة أسرع.
- **يقرأ Greenhouse قائمة لوحات أوسع عند الطلب.** يسمّي `sources.greenhouse.boards` اللوحات التي تريدها. اضبط `sources.greenhouse.discovery: broad` لكشط قائمة الـ619 معرّفًا المرفقة في `data/sources/greenhouse_slugs_broad.txt` أيضًا، ويضيف Sweepy أي لوحة يسميها ملفك الشخصي بالفعل. ويضبط `sources.greenhouse.concurrency` عدد اللوحات التي يقرأها Sweepy في وقت واحد: 20 في الوضع الواسع، و1 في غير ذلك. ويسحب الفحص الواسع كثيرًا من استجابات HTTP 404 بحكم التصميم. ويبلّغ Sweepy عن عدد الإخفاقات وأول عشرة معرّفات في تحذير واحد بدلًا من سطر لكل لوحة.
- **تبقى الخوادم الوسيطة اختيارية لكل محرك.** يقرأها المعالج من ملف أو يقبل واحدًا مباشرة، ويخفي كلمة المرور أثناء كتابتها، ولا يطبع محتواها أبدًا. ولا يقدّم `hirehunt` خيار خادم وسيط، لذا يسجل Sweepy تحذيرًا عندما يضبط ملف شخصي خادمًا وسيطًا.
- **يبدأ التخزين المؤقت مفعّلًا.** يعيد استعلام متكرر بالمحركات والإعدادات نفسها النتائج السابقة لمدة ساعة. أوقفه بـ `cache.enabled: false`، أو قصّر `ttl_seconds`.
- **تتوقف المهل عند الحد.** لا يستطيع Python إيقاف خيط محظور بالفعل داخل استدعاء مكتبة. يتوقف Sweepy عن الانتظار ويمضي، وتطبّق كل مكتبة مهل HTTP الخاصة بها في الأسفل.
- **يتخطى قاطع الدائرة محركًا فاشلًا.** بعد خمسة إخفاقات متتالية، يتوقف Sweepy عن استدعاء ذلك المحرك مدة 30 ثانية ويبلّغ عنه في `skipped_sources`.

### <a name="reported-postings"></a>الإعلانات المعروضة

يسجّل Sweepy كل إعلان يعرضه ويتخطى الإعلان نفسه في الجولة التالية. ويخزّن السجل في `~/.sweepy/history.db`، بنطاق لكل ملف شخصي. اضبط `SWEEPY_HISTORY_PATH` لتخزينه في مكان آخر. وتعرض شاشة **إعدادات الجولة** في المعالج مفتاح التشغيل والإيقاف ونافذة الاحتفاظ.

```yaml
history:
  enabled: true
  retention_days: 4   # 0 reports every posting on every run
  match: url+role     # url (strict) or url+role (default)
  path: null          # null uses ~/.sweepy/history.db
```

- **الاحتفاظ هو وتيرة إعادة العرض.** يخفي Sweepy الإعلان حتى تمر `retention_days`، ثم يعرضه مرة أخرى. ويعود الإعلان الحي باستمرار كل أربعة أيام على الأكثر.
- **المطابقة متسامحة افتراضيًا.** يقارن Sweepy عناوين URL الأساسية بعد إزالة معاملات التتبع والأجزاء. ثم يعود إلى العنوان والشركة والموقع بعد التطبيع، فتُحتسب إعادة النشر على لوحة أخرى الدور نفسه. اضبط `match: url` لاشتراط مطابقة عنوان URL أساسي.
- **لا تدخل السجل إلا الإعلانات الحية.** يدخل الإعلان السجل بعد أن يجتاز عنوانه التحقق. ولا تصبح الروابط المنتهية غير مرئية أبدًا.
- **يحصل مستدعو MCP على الافتراضي نفسه.** يبلّغ `run_sweep` عن `previously_seen_count` و`new_count`. مرّر `include_seen=true` لمراجعة الإعلانات السابقة، أو استدعِ `clear_history` لنسيانها. ويقبل `create_profile` الوسيط `history_config`.

### <a name="adding-another-engine"></a>إضافة محرك آخر

1. أنشئ `engine/adapters/<name>_adapter.py` واشتق منه الصنف `ScraperAdapter`.
2. اضبط `name`، والعلامات الثلاث `supports_*`، و`default_concurrency`، و`library`.
3. اكتب `preflight()` لفحص الإعدادات و`scrape()` لإرجاع DataFrame.
4. سجّله في `engine/adapters/__init__.py`.
5. صفه في `engine/engines.py` ليتمكن المعالج من عرضه وتثبيته.
6. أضف كتلة إعدادات إلى `engine/sweep_config.py` ومطالبة إلى `_ENGINE_PROMPTS` في `engine/config.py`.
7. أضف الحزمة إلى `requirements-engines.txt` وإلى إضافات pyproject.
8. اختبر المحوّل منفردًا، ثم فعّله وحده خلال جولة.

يتولى المنسّق الباقي. يوزّع الاستدعاءات بالاسم ويفرض المهلة. ويطبّع أي إطار يعود.

## <a name="agent-judgment"></a>حكم الوكيل

يقيّم Sweepy الإعلانات بالمفردات المشتركة، وذلك التقييم لا يستدعي نموذجًا ولا يستخدم الشبكة. وتنتج المدخلات نفسها الدرجة نفسها، وهي تقيس الصياغة لا الملاءمة. ويعامل خادم MCP تقييم الوكيل كالمسار المتوقع.

لا يستدعي `run_sweep` نموذجًا. يعيد `assessment_mode: "agent"` و`assessment_required: true` و`assessed_count: 0`. ويستمر سير العمل بـ `get_jobs`، ثم تقييم مستقل لكل دور مقابل السيرة الذاتية، ثم `submit_judgments`، ثم `render_report`. مرّر كل حكم في قائمة `judgments` واحدة لإبقاء تقييم 24 دورًا في استدعاء واحد. وتعرض البطاقات المقيَّمة `NN% MATCH`. وتحتفظ البطاقات غير المقيَّمة بـ `NN% KEYWORD OVERLAP`.

يعيد `get_jobs` الحقل `resume_documents` مع النص المحلَّل لكل مسار سيرة ذاتية. احكم على ذلك النص، لا على `must_have_skills` و`synonyms` في الملف الشخصي، فهما يغذيان تمريرة الكلمات المفتاحية الحتمية فقط. اقرأ المستند كما يقرأه مسؤول التوظيف: المهارات القابلة للنقل، ونطاق كل بند ومستوى أقدميته، والمجال، والأدوات، والنتائج التي يثبتها. ثم قيّمه كما يحلله نظام تتبع المتقدمين في الإعلان. ويعد المحلل أي عبارة يجدها في قسم خبرة أو مهارات قياسي دليلًا. أما العبارة نفسها داخل جدول أو رأس أو تذييل أو صورة أو شريط جانبي بعمودين فقد لا تصل إلى إنسان أبدًا، لذا وزنها أقل. ويسمّي Sweepy عائلة ATS عندما يكشفها عنوان URL للتقديم، ويسجل الحكم ما سيفقده المحلل.

يقيس `match_pct` المؤهلات، لذا تبقى تفاصيل التوظيف خارجها. وتنتمي ساعات العمل الجزئي وحالة العقد والموقع إلى `concerns`. ولا يفقد الدور الذي يستطيعه المرشح نقاطًا إلا عندما لا تطابق المهارات أو الخبرة المتطلبات المعلنة في الإعلان. ويقيس الترتيب عندئذ الملاءمة لا الإتاحة.

قيّم جانبي الحالة. يذكر `alignment` أبرز نقطة، أقوى دليل على ملاءمة المرشح. ويذكر `concerns` ما يعمل ضد المرشح، مثل مؤهل ناقص، أو فجوة في مدة العمل، أو ساعات جزئية، أو مدة عقد، أو موقع يستلزم الانتقال، أو أجر أقل من الحد الأدنى. ويطبع التقرير الزوجين في سطر واحد تحت صف المتطلبات، ويكتسب ملف CSV عمودًا باسم `concerns`. وتملأ جولة الكلمات المفتاحية وحدها `concerns` من كلمات الإعلان التي تفوت السيرة الذاتية.

تقبل `submit_judgments` أيضًا الوسيط `portfolio_highlight`. مرّر أعمال ملف الأعمال الخاصة بذلك الإعلان، فتطبعها البطاقة بوصفها **أبرز نقطة**. أما البطاقة التي لا تتلقى أبرز نقطة مُرسلة، فتسرد الأعمال التي وجدها Sweepy.

## <a name="portfolio-support"></a>دعم ملف الأعمال

يقرأ Sweepy ملف الأعمال مرة واحدة في كل جولة ويسرد أعماله على كل بطاقة. ويجمع ملف الأعمال قبل بناء الملف الشخصي. أعطه عنوان URL على الإنترنت أو ملفًا محليًا بصيغة `.pdf` أو `.docx` أو `.md` أو `.txt` أو `.html`. ومرّر مدخلًا واحدًا لكل مسار سيرة ذاتية عندما تستهدف أكثر من عائلة أدوار.

```yaml
portfolio:
  # One entry per resume track. An entry without `track` serves every track.
  sources:
    - track: "UX Writer Resume"
      url: "https://example.com/work"
    - track: "Technical Writer Resume"
      path: "C:/portfolios/technical-writing.pdf"
  pieces_per_card: 3
```

يجلب Sweepy ملف الأعمال على الإنترنت ليقرأ عناوينه وروابطه. وعندما تحجب صفحة الطلب، تحتفظ البطاقة بالرابط وتتخطى قائمة الأعمال. وتعرض بطاقة PDF ملف الأعمال وأعماله. وتضيف صادرات CSV وJSON الحقول `portfolio_url` و`portfolio_pieces` و`portfolio_highlight`.

لإرفاق ملف أعمال بملف شخصي محفوظ، استدعِ `set_portfolio` من MCP أو أجب عن خطوة ملف الأعمال في المعالج. ويقبل الإعداد غير التفاعلي `--portfolio` و`--portfolio-track`.

تأخذ `render_report` الوسيط `playbook` لمربع استراتيجية الختام. اكتب نثرًا بسيطًا. يهرّب Sweepy علامات العطف ويحوّل الأسطر الجديدة إلى فواصل أسطر. وتُعرض `**bold**` كنص عريض، وتصبح الأقواس الزاوية نصًا عاديًا. ويخزّن Sweepy دليل اللعب مع الجلسة، ويعيد العرض اللاحق استخدامه بدلًا من المولَّد. وإطلاق جولة جديدة يمسحه.

في الوضع `agent`، ترفض `render_report` بناء تقرير مختلط. تعيد خطأً يسرد معرّفات الوظائف غير المقيَّمة. ويقرأ المساعد تلك القائمة ويرسل أحكامًا للمعرّفات الناقصة. والملفات الشخصية التي تريد تقارير كلمات مفتاحية وحدها تضبط `report.assessment: "keyword"`. وتعرض جولة سطر الأوامر تداخل الكلمات المفتاحية أيضًا، لأن لا وكيل يقدّم أحكامًا. اضبط `SWEEPY_REQUIRE_JUDGMENTS=1` عندما يجب أن تسري البوابة على كل ملف شخصي وعلى `export_report` كذلك.

تكشط الجولة الحية اللوحات لمدة دقيقة أو أكثر. ويشغّلها خادم MCP في الخلفية. ينتظر `run_sweep` 45 ثانية على الأكثر ثم يعيد `sweep_status: "running"` مع `job_id`. استعلم `get_sweep_status` دوريًا حتى يبلّغ `completed`. وتستمر الجولة إذا انقطع العميل. واضبط `SWEEPY_MCP_WAIT_SECONDS` لتقليل الانتظار في المضيفات ذات مهل الأدوات الأضيق.

تستخدم الملفات الشخصية المنشأة عبر MCP المحركات المدمجة مع المحركات الاختيارية المثبّتة التي تجتاز
فحوص إعداداتها الافتراضية. قدّم `sources_config` لاختيار المحركات
صراحةً. يحتاج OpenRoles معرّفًا لكل شركة. ويحتاج Apify موافقة صريحة
لأنه قد يترتب على ذلك رسوم.

يستطيع المساعد التحقق من النتائج وملء الفجوات بأدوات البحث لديه. ينبغي أن يفحص المصادر والإعلانات المتخطاة مقابل صفحات التوظيف لدى أصحاب العمل. وينبغي أن يضيف ما تحقق من عناصر ناقصة وأن يوسم الإعلانات غير المتاحة بأنها غير مؤكدة. ويجب أن يعلن عندما لا يستطيع تأكيد التغطية الكاملة.

راجع [تكامل MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration) لخطوات الإعداد.

تنشر كل أداة MCP تلميحات للقراءة فقط والتدمير والتكرارية والعالم المفتوح. وتقرأ المضيفات المتوافقة تلك التلميحات قبل استدعاء الأداة.

## <a name="before-you-upload-your-resume"></a>قبل رفع سيرتك الذاتية

يحدد تخطيطك مقدار النص الذي يستطيع Sweepy قراءته. تصميم بعمودين أو جدول أو صفحة ممسوحة يشوّش النص الذي يقرأه المحرك ويخفض درجاتك. ويستخرج العمود الواحد النظيف المحتوى النصي الحقيقي بأعلى موثوقية، وتقرأه أنظمة تتبع المتقدمين بالطريقة نفسها.

اقرأ [نصائح تنسيق السيرة الذاتية](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips) قبل جولتك الأولى.

## <a name="documentation"></a>التوثيق

### <a name="getting-started"></a>البدء

- [المقدمة](https://pvega62.github.io/software/docs/sweepy/intro)
- [التثبيت](https://pvega62.github.io/software/docs/sweepy/installation)
- [الإعداد](https://pvega62.github.io/software/docs/sweepy/setup)
- [تشغيل جولتك الأولى](https://pvega62.github.io/software/docs/sweepy/first-sweep)
- [فهم نتائجك](https://pvega62.github.io/software/docs/sweepy/understanding-results)

### <a name="resumes-and-match-scores"></a>السير الذاتية ودرجات المطابقة

- [نصائح تنسيق السيرة الذاتية](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)
- [التقييم والحدود](https://pvega62.github.io/software/docs/sweepy/guides/scoring-and-limits)

### <a name="command-and-configuration-reference"></a>مرجع الأوامر والإعدادات

- [الأوامر والعلامات](https://pvega62.github.io/software/docs/sweepy/reference/cli-reference)
- [مرجع الإعدادات](https://pvega62.github.io/software/docs/sweepy/reference/configuration-reference)
- [مصادر الوظائف والمنصات](https://pvega62.github.io/software/docs/sweepy/reference/sources-and-platforms)
- [تكامل MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)
- [مرجع أدوات MCP](https://pvega62.github.io/software/docs/sweepy/reference/mcp-tool-reference)
- [مرجع المطورين](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## <a name="legal-and-responsible-use"></a>الاستخدام القانوني والمسؤول

يكشط Sweepy لوحات الوظائف العامة وواجهات برمجة لوحات الوظائف. وقد يخالف الكشط شروط الخدمة لدى بعض المنصات. راجع تلك الشروط قبل الاعتماد على الأداة.

- استخدمه في **البحث الشخصي عن الوظائف**. لا تستخدمه في الجمع أو إعادة التوزيع بالجملة.
- احترم حدود المعدل. يرسل Sweepy وكيل مستخدم مهذبًا وتأخيرًا قصيرًا بين الطلبات. وزد التأخير بمتغير البيئة `SWEEPY_SOURCE_DELAY`.
- لا يقدّم Sweepy استشارة قانونية.

يجري الكشط عبر [`python-jobspy`](https://github.com/Bunsly/JobSpy)، وعند تثبيتها [`hirehunt`](https://pypi.org/project/hirehunt/)، و[`openroles`](https://pypi.org/project/openroles/)، و[`jobdrop`](https://pypi.org/project/jobdrop/)، و[Apify](https://apify.com/). وينشر كل مشروع ملاحظات استخدامه. وقد يخالف كشط Google Jobs وLinkedIn وIndeed وGlassdoor شروط الخدمة لتلك المنصات. وينقل Apify الطلب إلى خدمة مُدارة. ولا يغيّر ذلك المخاطر القانونية.

## <a name="license"></a>الترخيص

يصدر Sweepy بموجب [رخصة MIT](LICENSE).
