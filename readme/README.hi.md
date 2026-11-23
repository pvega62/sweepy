                                  ████  █   █  ████  ████  ████  █   █
                                  █     █   █  █     █     █  █  █   █
                                  ████  █ █ █  ███   ███   ████   █ █ 
                                    █  ██ ██  █     █     █       █  
                                  ████  █   █  ████  ████  █       █  
<h1 align="center">Sweepy: मल्टी-इंजन जॉब सर्च और स्कोरिंग</h1>

<p align="center">
  <strong>और स्मार्ट, बेहतर, तेज़ और मज़बूत तरीके से खोजें।</strong><br>
  टॉप प्लेटफ़ॉर्म पर समानांतर जॉब स्क्रैपिंग, अपने-आप रिज़्यूमे स्कोरिंग, और रैंक वाली रिपोर्टिंग।
</p>

<p align="center">
  <a href="https://github.com/pvega62/sweepy/actions"><img src="https://github.com/pvega62/sweepy/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10 या उससे नया"></a>
  <a href="../LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT लाइसेंस"></a>
  <a href="https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme"><img src="https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271" alt="M8ven स्कोर"></a>
</p>

<p align="center">
  <a href="#quick-start"><strong>क्विक स्टार्ट</strong></a> ·
  <a href="#features">विशेषताएँ</a> ·
  <a href="#job-engines">जॉब इंजन</a> ·
  <a href="#portfolio-support">पोर्टफ़ोलियो सपोर्ट</a> ·
  <a href="#documentation">डॉक्यूमेंटेशन</a> ·
  <a href="https://github.com/pvega62/sweepy/issues/new">समस्या रिपोर्ट करें</a>
</p>

<p align="center">
  <a href="../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <strong>हिन्दी</strong> · <a href="README.ja.md">日本語</a> · <a href="README.ar.md">العربية</a> · <a href="README.zh.md">简体中文</a>
</p>

---

Sweepy एक मुफ़्त टूल है जो जॉब बोर्ड खोजता है और हर पोस्टिंग को आपके रिज़्यूमे के सामने स्कोर करता है। यह कंपनियों की करियर साइट और जॉब बोर्ड पढ़ता है, डुप्लिकेट और एक्सपायर हुई लिस्टिंग हटाता है, फिर रैंक वाली रिपोर्ट लिखता है। प्रोफ़ाइल बदले बिना आप एक स्वीप के लिए डुप्लिकेट जाँच बंद कर सकते हैं। सेटअप विज़ार्ड एक लॉन्चपैड खोलता है: सर्च, प्रोफ़ाइल सेटअप, सर्च ट्यूनिंग, और Sweepy के Toolbox कार्य जैसे इंजन और एग्रीगेटर मैनेजमेंट।

> मौजूदा वर्ज़न और रिलीज़ इतिहास के लिए **[CHANGELOG.md](../CHANGELOG.md)** देखें।

## <a name="features"></a>विशेषताएँ

- **एक साथ कई जगह खोजता है।** Greenhouse, Ashby, Lever, Workable, Built In NYC, LinkedIn, Indeed, Glassdoor, और ZipRecruiter से पोस्टिंग जुटाता है। इनमें से हर सोर्स API key के बिना काम करता है।
- **हर इंजन समानांतर चलाता है।** चालू इंजन एक साथ शुरू होते हैं। तब एक स्वीप सबसे धीमे इंजन जितना समय लेता है, उनके जोड़ जितना नहीं।
- **बोर्ड फेल होने पर भी चलता रहता है।** हर इंजन को एक टाइमआउट और सर्किट ब्रेकर मिलता है। एक फेल होता एंडपॉइंट रन रोक नहीं सकता और न ही वही रिक्वेस्ट पाँच बार दोहराता है।
- **ज़रूरत पर और इंजन जोड़ता है।** टर्मिनल छोड़े बिना विज़ार्ड से HireHunt, openroles, jobdrop, या Apify इंस्टॉल करें।
- **हर पोस्टिंग को आपके रिज़्यूमे के सामने स्कोर करता है।** आपके PDF या Word रिज़्यूमे का टेक्स्ट पढ़ता है और मापता है कि उसका कितना हिस्सा पोस्टिंग से मेल खाता है।
- **एक्सपायर लिंक हटाता है।** हर URL जाँचता है और वे पोस्टिंग हटाता है जो अब मौजूद नहीं हैं।
- **बोर्ड्स के बीच डुप्लिकेट पोस्टिंग जाँचता है।** नॉर्मलाइज़ किए गए जॉब टाइटल, कंपनी, और लोकेशन मिलाता है, तब भी जब बोर्ड अलग URL इस्तेमाल करते हैं। एक रन के लिए हर बोर्ड की लिस्टिंग रखने हेतु `--no-dedupe` पास करें।
- **वे पोस्टिंग छोड़ देता है जो आप पहले देख चुके हैं।** रोज़ का स्वीप कल की लिस्ट के बजाय नई भूमिकाएँ रिपोर्ट करता है। Sweepy रिपोर्ट की गई पोस्टिंग को चार दिन की विंडो तक दबा देता है। उन्हें एक रन के लिए वापस लाने हेतु `--include-seen` पास करें।
- **आपको सही रिज़्यूमे तक पहुँचाता है।** हर जॉब को उस रिज़्यूमे ट्रैक पर भेजता है जो आपने उस भूमिका के लिए लिखा है, फिर कार्ड को रंगीन बैज से लेबल करता है।
- **आपके पोर्टफ़ोलियो को हर फ़ैसले का हिस्सा बनाता है।** Sweepy को ऑनलाइन पोर्टफ़ोलियो या लोकल PDF, Word, Markdown, टेक्स्ट, या HTML फ़ाइल पर इंगित करें। हर कार्ड उस पोर्टफ़ोलियो के पीस दिखाता है। जब आप एक से ज़्यादा तरह की भूमिकाओं के लिए अप्लाई करते हैं, तो हर रिज़्यूमे ट्रैक के लिए एक पोर्टफ़ोलियो रखें।
- **काम आने वाली रिपोर्ट बनाता है।** क्लिक करने योग्य लिंक वाला एक-कार्ड-प्रति-पेज PDF, साथ में अपनी ट्रैकिंग के लिए CSV और JSON फ़ाइलें बनाता है।
- **CSV को अप्लिकेशन ट्रैकर में बदलता है।** CSV `date_applied`, `status`, `interview_stage`, `offer_amount`, `offer_date`, `follow_up_date`, `contact`, और `notes` पर खत्म होती है। इन्हें Excel, Google Sheets, या Notion से भरें। Sweepy आपकी एंट्री उसी प्रोफ़ाइल के बाद के स्वीप में कॉपी करता है। PDF आपको एक रैंक वाली पढ़ने की सूची देता है जिसमें हर कार्ड पर अप्लाई लिंक होते हैं। स्प्रेडशीट PDF की कार्ड सीमा से आगे की भूमिकाएँ रखती है और दर्ज करती है कि आपने हर एक के बारे में क्या किया। कॉलम `export.tracking: false` से बंद करें।

## <a name="quick-start"></a>क्विक स्टार्ट

आपके पास **Python 3.10 या उससे नया** होना चाहिए। Python 3.13 पर कुछ पैकेज सोर्स से बनते हैं। आपको पहले Microsoft C++ Build Tools चाहिए हो सकते हैं। [Sweepy इंस्टॉल करना](https://pvega62.github.io/software/docs/sweepy/installation) देखें।

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

`pip install -e .` हर कोर डिपेंडेंसी इंस्टॉल करता है और आपके Python Scripts फ़ोल्डर में `sweepy` कमांड रजिस्टर करता है। एक बार टर्मिनल दोबारा खोलें ताकि आपका शेल उस फ़ोल्डर को PATH से उठा ले। विज़ार्ड शुरू करने के लिए `sweepy` चलाएँ, या कोई कमांड ऑप्शन जोड़ें जैसे `sweepy --run`। आप स्क्रिप्ट सीधे `python swee.py` से भी चला सकते हैं।

वह एक कमांड आपको दो बिल्ट-इन इंजन देता है। ज़रूरत पड़ने पर विज़ार्ड चार ऑप्शनल इंजन पेश करता है, और आपको कभी हाथ से दूसरी requirements फ़ाइल इंस्टॉल करने की ज़रूरत नहीं पड़ती।

इसके बजाय हर संगत इंजन पहले से खींचने के लिए, उसी कमांड में एक फ़्लैग जोड़ें:

```bash
pip install -e ".[all-engines]"
```

यह एक ही रिज़ॉल्यूशन में HireHunt, openroles, और Apify जोड़ता है। `jobdrop` बाहर रहता है क्योंकि उसका मेटाडेटा JobSpy के साथ रिज़ॉल्व नहीं हो सकता। जब आपको उसके 33 बोर्ड चाहिए, तो इसे `sweepy --install-engines jobdrop --allow-engine-conflicts` से इंस्टॉल करें। [जॉब इंजन](#job-engines) सेक्शन दोनों रास्ते बताता है।

`sweepy` चलाने पर विज़ार्ड का टाइल-आधारित लॉन्चपैड खुलता है। **Start Sweep**, **Build Profile**, **Load Profile**, **Sweep Settings**, **Sweepy's Toolbox**, और **Exit Sweepy** के बीच जाने के लिए एरो कीज़ इस्तेमाल करें, फिर Enter दबाएँ। टाइल के सबटाइटल सादे शब्दों में कार्य बताते हैं, जैसे **Run your job search now** या **Open a search you saved**। **Load Profile** आपको अगले स्वीप के लिए सेव की गई प्रोफ़ाइल चुनने देता है। टूलबॉक्स में प्रोफ़ाइल एडिटिंग, इंजन मैनेजमेंट, डीबग लॉगिंग, हेल्प, हाल के लॉग, डॉक्यूमेंट कन्वर्ज़न, और अपडेट शामिल हैं। **Build Profile** आपका नाम, टारगेट जॉब टाइटल, लोकेशन, और रिज़्यूमे पाथ जुटाता है। पूरा करने पर विज़ार्ड प्रोफ़ाइल सेव करता है। प्रोफ़ाइल सीधे एडिट करने के लिए `sweepy --setup --profile profiles/your_profile.yaml` चलाएँ।

सबमेन्यू **← Back** के साथ खुलते हैं, जो उन्हें खोलने वाले मेन्यू पर लौटाता है। Esc भी वही करता है। किसी सवाल पर Esc पिछला जवाब फिर खोलता है। सबमेन्यू के अंदर Esc एक स्तर ऊपर जाता है। लॉन्चपैड पर Esc बाहर निकलता है। Ctrl+C कहीं से भी क्विट करता है।

जब नया वर्ज़न रिलीज़ हो तो नया कोड खींचने के लिए चलाएँ:

```bash
sweepy --update
```

Sweepy आपका Git रिमोट जाँचता है और चेकआउट को फ़ास्ट-फ़ॉरवर्ड करता है। यह `requirements.txt` और आपके पहले से इंस्टॉल किए गए ऑप्शनल इंजन दोबारा इंस्टॉल करता है। यह बिना कमिट किए बदलावों वाला चेकआउट बदलने से मना कर देता है। कुछ भी बदले बिना नया वर्ज़न जाँचने के लिए `sweepy --check-update` बेहतर है।

फिर अपना पहला स्वीप चलाएँ:

```bash
sweepy --run
```

`--run` आपकी आखिरी सेव की गई प्रोफ़ाइल से स्वीप करता है। दूसरी प्रोफ़ाइल चुनने के लिए `sweepy --profile profiles/your_profile.yaml` इस्तेमाल करें।

प्रोफ़ाइल सेटिंग बदले बिना एक रन के लिए डुप्लिकेट जाँच बंद करें:

```bash
sweepy --run --no-dedupe
sweepy --profile profiles/your_profile.yaml --no-dedupe
```

डिफ़ॉल्ट रूप से Sweepy एक ही पोस्टिंग रखता है जब अलग बोर्ड एक ही नॉर्मलाइज़ टाइटल, कंपनी, और लोकेशन दिखाते हैं। Model Context Protocol (MCP) का `run_sweep` टूल उसी प्रति-रन ओवरराइड के लिए `deduplicate=false` स्वीकार करता है।

Sweepy पहले के स्वीप की पोस्टिंग भी छिपाता है। उन्हें दोबारा देखें या नए सिरे से शुरू करें:

```bash
sweepy --run --include-seen      # report earlier postings too
sweepy --run --reset-history     # forget them, then sweep
sweepy --reset-history           # forget the last profile's history and exit
```

Sweepy को स्क्रिप्ट करते समय बिना प्रॉम्प्ट के प्रोफ़ाइल बनाएँ या अपडेट करें:

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

Sweepy फ़ाइल लिखने से पहले चालू इंजन वैलिडेट करता है। ज़रूरी फ़ील्ड छूटे तो कारण के साथ तुरंत फेल होता है। इंटरैक्टिव विज़ार्ड में OpenRoles कंपनी slugs खाली छोड़कर वह इंजन छोड़ें। OpenRoles सिर्फ नामित कंपनी बोर्ड खोजता है। OpenRoles चालू करने वाली नॉन-इंटरैक्टिव प्रोफ़ाइल को फिर भी `--openroles-companies` चाहिए। नॉन-इंटरैक्टिव फ़्लैग में `--sources`, `--jobspy-sites`, `--hirehunt-sources`, `--jobdrop-sites`, `--openroles-companies`, `--apify-actor`, `--timeout`, `--cache-ttl`, `--no-cache`, `--history-days`, `--no-history`, और `--job-tracking` / `--no-job-tracking` शामिल हैं।

जब आप प्रॉम्प्ट और टूल कॉल के बजाय एडिटर पसंद करते हैं तो प्रोफ़ाइल फ़ाइल भरें:

```bash
cp profiles/template_custom.yaml profiles/my_search.yaml
# replace the four REQUIRED values, then run the copy
sweepy --profile profiles/my_search.yaml
```

टेम्पलेट हर सेटिंग को उसके डिफ़ॉल्ट के साथ दस्तावेज़ करता है। डिस्कवरी शुरू होने से पहले Sweepy आपका नाम, टाइटल, और लोकेशन प्रिंट करता है। टाइपो पहली आउटपुट लाइन पर दिख जाता है।

विज़ार्ड खोले बिना रिज़्यूमे या नोट्स फ़ाइल को PDF में बदलें:

```bash
sweepy --convert path/to/resume.docx
```

`--convert` `.docx`, `.doc`, `.txt`, `.md`, और `.pdf` फ़ाइलें स्वीकार करता है। यह PDF को मूल फ़ाइल के बगल में लिखता है और अंतिम पाथ प्रिंट करता है।

एक स्वीप में 30 से 90 सेकंड लगते हैं। Sweepy काम करते समय अपनी प्रगति प्रिंट करता है:

1. **आपकी प्रोफ़ाइल लोड करता है।**
2. **आपके चालू किए प्लेटफ़ॉर्म पर ओपनिंग खोजता है।**
3. **लिंक वैलिडेट करता है** और एक्सपायर हुए हटा देता है।
4. **हर भूमिका को स्कोर करता है** आपके रिज़्यूमे के सामने।
5. **आपकी रिपोर्ट लिखता है।**

## <a name="what-you-get"></a>आपको क्या मिलता है

हर रन `results/` फ़ोल्डर में तारीख वाली फ़ाइलें लिखता है। पुरानी रिपोर्ट अपनी जगह रहती हैं। MCP से चलने वाला स्वीप फ़ाइलनाम में `mcp` जोड़ता है, जैसे `paralegal_nyc_mcp_2026-10-27-223115.pdf`। स्टैम्प आपकी मशीन की घड़ी मानता है। दूसरे ज़ोन में फ़ाइलें नाम देने के लिए `export.timezone` सेट करें।

- **एक PDF रिपोर्ट।** हर भूमिका के लिए एक कार्ड, मैच स्कोर से सॉर्ट किया गया, जिसमें पे, बेनिफ़िट, और अप्लाई करने का लिंक होता है।
- **एक CSV फ़ाइल।** हर कार्ड फ़ील्ड, पूरा पोस्टिंग बॉडी, और आठ जॉब-ट्रैकिंग कॉलम जो Sweepy बाद के स्वीप में कॉपी करता है। इसे Excel, Google Sheets, या Notion में खोलें। छोटी फ़ाइलें चाहिए तो `export.description_chars` को धनात्मक संख्या पर सेट करें। कटी हुई बॉडी छोड़े गए अक्षरों की गिनती बताने वाले नोट पर खत्म होती है।
- **एक JSON फ़ाइल।** वही डेटा ऐसे फ़ॉर्मैट में जिसे दूसरे टूल पढ़ सकें।

[सैंपल PDF](../docs/sample_report.pdf) खोलें, या [पेज 1 को इमेज के रूप में](../docs/sample_report.png) देखें।

## <a name="job-engines"></a>जॉब इंजन

Sweepy में दो इंजन शामिल हैं और चार और डाउनलोड कर सकता है। `ats` इंजन applicant tracking system (ATS) को सीधे पढ़ता है। हर इंजन एक ही एडाप्टर के पीछे चलता है। प्रोफ़ाइल एक जैसी दिखती हैं, चाहे पोस्टिंग किसी भी इंजन ने खोजी हो।

| इंजन | उपलब्धता | क्या स्क्रैप करता है | प्रॉक्सी | User-Agent | विवरण |
|---|---|---|---|---|---|
| `jobspy` | बिल्ट इन | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | हाँ | हाँ | टॉगल |
| `ats` | बिल्ट इन | Greenhouse, Ashby, Lever, Workable, BuiltinNYC | नहीं | नहीं | हमेशा |
| `hirehunt` | डाउनलोड | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, और छह कंपनी बोर्ड (Google Careers, Amazon, Meta, Apple, Netflix, Microsoft) | नहीं | नहीं | हमेशा |
| `openroles` | डाउनलोड | Greenhouse, Lever, Ashby, आपके नामित Workday बोर्ड | नहीं | नहीं | हमेशा |
| `jobdrop` | डाउनलोड | Google, Wellfound, Workday, iCIMS, Dice, USAJobs सहित 33 बोर्ड | हाँ | हाँ | टॉगल |
| `apify` | डाउनलोड | मैनेज्ड actors, डिफ़ॉल्ट रूप से LinkedIn | actor संभालता है | actor संभालता है | actor पर निर्भर |

`jobdrop` JobSpy के साथ मेटाडेटा कॉन्फ़्लिक्ट बताता है: यह `curl-cffi<0.8` पिन करता है, जबकि JobSpy को `curl_cffi>=0.16.2` चाहिए। पिन पुराना है। `jobdrop` नई लाइब्रेरी पर ठीक चलता है, जिसमें अब भी वे सभी impersonation प्रोफ़ाइल हैं जो वह इस्तेमाल करता है (`safari17_2_ios`, `chrome120`, `chrome124`)।

दोनों का सादा `pip install` अब भी फेल होता है। `--install-engines all` `jobdrop` बाहर रखता है। इसे समर्थित तरीके से इंस्टॉल करने के लिए `--allow-engine-conflicts` जोड़ें। Sweepy `jobdrop` को `--no-deps` के साथ इंस्टॉल करता है, फिर उसकी बाकी ज़रूरतें रिज़ॉल्व करता है, इसलिए `curl_cffi` JobSpy के वर्ज़न पर रहता है और दोनों इंजन चलते हैं।

```bash
sweepy --install-engines all
sweepy --install-engines openroles,apify
sweepy --install-engines jobdrop --allow-engine-conflicts
```

उस इंस्टॉल के बाद भी `pip check` `jobdrop` की पुरानी ऊपरी सीमा बताता है। यह चेतावनी मेटाडेटा के बारे में है, चल रहे कोड के बारे में नहीं।

या विज़ार्ड खोलें और **Sweepy's Toolbox** फिर **Download job engines** चुनें। वह स्क्रीन हर इंजन के बोर्ड और इंस्टॉल स्थिति दिखाती है। यह `pip` चलाने से पहले पूछती है। प्रोफ़ाइल बनाते समय कोई छूटा इंजन चुनें और विज़ार्ड वही डाउनलोड पेश करता है। Sweepy आपकी पुष्टि के बिना कभी इंस्टॉल नहीं चलाता।

### <a name="disk-footprint"></a>डिस्क फुटप्रिंट

Windows पर Python 3.13 के साथ मापा गया:

| इंस्टॉल | डिस्क पर पैकेज | नोट्स |
|---|---|---|
| Core (`requirements.txt`) | 283 MB | 53 पैकेज, जिनमें pandas, pymupdf, और MCP SDK शामिल हैं |
| `hirehunt` | +13 MB | rich और markdown-it-py जोड़ता है |
| `openroles` | +0.3 MB | सिर्फ Python स्टैंडर्ड लाइब्रेरी |
| `apify-client` | +14 MB | impit और more-itertools जोड़ता है |
| `jobdrop` | +406 MB | scipy (134 MB), playwright (113 MB), tls-client (93 MB), और selenium (34 MB) की अगुवाई में |

संगत इंजनों का पूरा इंस्टॉल लगभग **310 MB** लेता है। `jobdrop` जोड़ने से ब्राउज़र डाउनलोड होने से पहले कुल लगभग **716 MB** हो जाता है।

ब्राउज़र बाइनरी Python एनवायरनमेंट के बाहर रहते हैं और पहले इस्तेमाल पर आते हैं:

- Playwright का Chromium बिल्ड लगभग **710 MB** है (Chromium और उसका headless shell)।
- Firefox और WebKit सहित पूरा Playwright सेट लगभग **1.2 GB** लेता है।
- Camoufox, जिसे `jobdrop` अपने स्टेल्थ पाथ के लिए इस्तेमाल करता है, पहली लॉन्च पर पैच किया हुआ Firefox डाउनलोड करता है।

Sweepy हर बिल्ट-इन इंजन बिना ब्राउज़र के चलाता है। कोर इंस्टॉल को उस जगह की ज़रूरत नहीं है।

कभी भी इंजन और उनकी इंस्टॉल स्थिति देखें:

```bash
sweepy --list-engines
```

`openroles` आपके नामित बोर्ड पढ़ता है और कंपनी slugs माँगता है। `apify` `APIFY_TOKEN` एनवायरनमेंट वेरिएबल पढ़ता है और आपके Apify अकाउंट पर बिल करता है।

किसी इंजन को इंस्टॉल करना उसे चालू नहीं करता। उसे तीन में से एक तरीके से प्रोफ़ाइल में जोड़ें:

1. **विज़ार्ड।** `sweepy` चलाएँ, **Sweepy's Toolbox** चुनें, फिर **Manage job engines**, फिर **Choose engines and settings**। इंस्टॉल किए इंजन `[installed]` टैग दिखाते हैं। किसी पर टिक करें और विज़ार्ड उसकी सेटिंग्स पूछता है।
2. **प्रोफ़ाइल एडिट।** प्रोफ़ाइल लोड करें, फिर रिव्यू स्क्रीन से **Manage job engines** चुनें।
3. **कमांड लाइन।** इंजन को `--sources` में नाम दें और उसकी सेटिंग्स दें:

```bash
sweepy --setup --non-interactive --profile profiles/your_profile.yaml \
  --sources jobspy,ats,jobdrop --jobdrop-sites linkedin,indeed,wellfound
```

हर रास्ता फ़ाइल लिखने से पहले इंजन की सेटिंग्स वैलिडेट करता है। कोई छूटी वैल्यू, जैसे `openroles` कंपनी slugs, टूटी प्रोफ़ाइल सेव करने के बजाय कारण के साथ फेल होती है।

### <a name="choosing-boards"></a>बोर्ड चुनना

प्रोफ़ाइल विज़ार्ड का प्लेटफ़ॉर्म स्टेप वे सभी बोर्ड दिखाता है जिन्हें Sweepy खोज सकता है, उन्हें पढ़ने वाले इंजन के नीचे समूहित करके। सभी 63 बोर्ड एक ही जगह दिखते हैं, केवल 13 बिल्ट-इन बोर्ड नहीं।

| समूह | बोर्ड | टैग |
|---|---|---|
| `jobspy` (8) | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | `built in` |
| `ats` (5) | Greenhouse, Ashby, Lever, Workable, BuiltinNYC | `built in` |
| `hirehunt` (12) | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, Google Careers, Amazon, Meta, Apple, Netflix, Microsoft | `needs download` जब तक इंस्टॉल न हो |
| `openroles` (4) | Greenhouse, Lever, Ashby, Workday | `needs download`, और कंपनी slugs चाहिए |
| `jobdrop` (33) | Google, Wellfound, Workday, iCIMS, Dice, USAJobs, Handshake, और अन्य | `needs download`, और JobSpy से कॉन्फ़्लिक्ट |
| `apify` (1) | Apify actor के ज़रिए LinkedIn | `needs download`, और `APIFY_TOKEN` चाहिए |

हर पंक्ति अपना इंजन और इंस्टॉल स्थिति दिखाती है, जैसे `Indeed  [jobspy · built in]` या `Wellfound  [jobdrop · needs download]`। चुनाव करने से पहले आप टैग देख लेते हैं। बिना लोकल इंस्टॉल वाले इंजन का बोर्ड टिक करें और विज़ार्ड उसे इंस्टॉल करने वाला कमांड प्रिंट करता है। इंस्टॉल किया इंजन इसके बजाय `installed` दिखाता है। सेव की प्रोफ़ाइल दोबारा खोलने पर उसके मौजूदा बोर्ड पहले से टिके दिखते हैं। Sweepy बिना इंस्टॉल वाले इंजन का बोर्ड प्रोफ़ाइल में रखता है, और इंस्टॉल पूरा होने तक स्वीप चेतावनी के साथ उस इंजन को छोड़ देता है।

### <a name="engine-settings"></a>इंजन सेटिंग्स

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

पुरानी प्रोफ़ाइल चलती रहती हैं। `sources.jobspy` के नीचे बोर्ड booleans अब भी अलग-अलग JobSpy बोर्ड चालू और बंद करते हैं। जिस प्रोफ़ाइल में `sources.enabled` सूची नहीं है वह डिफ़ॉल्ट रूप से JobSpy और बिल्ट-इन ATS रीडर पर जाती है।

- **विवरण डिफ़ॉल्ट रूप से चालू रहते हैं।** स्कोरिंग पोस्टिंग टेक्स्ट को आपके रिज़्यूमे के सामने मिलाती है। `fetch_descriptions` सिर्फ तब बंद करें जब आप तेज़ स्वीप के लिए कमज़ोर मैच स्वीकार करते हैं।
- **Greenhouse माँगने पर ज़्यादा बोर्ड पढ़ता है।** `sources.greenhouse.boards` उन बोर्ड के नाम देता है जो आप चाहते हैं। `sources.greenhouse.discovery: broad` सेट करके `data/sources/greenhouse_slugs_broad.txt` में बंडल की गई 619-slug सूची भी स्वीप करें, और Sweepy आपकी प्रोफ़ाइल में पहले से नामित हर बोर्ड भी जोड़ देता है। `sources.greenhouse.concurrency` तय करता है कि Sweepy एक बार में कितने बोर्ड पढ़ता है: broad मोड में 20, वरना 1। एक broad प्रोब डिज़ाइन से ही बहुत सारे HTTP 404 जवाब लाता है। Sweepy हर बोर्ड के लिए एक पंक्ति के बजाय एक चेतावनी में फेल्योर की गिनती और पहले दस slugs बताता है।
- **प्रॉक्सी हर इंजन के लिए ऑप्ट-इन रहते हैं।** विज़ार्ड उन्हें फ़ाइल से पढ़ता है या एक inline वैल्यू स्वीकार करता है, टाइप करते समय पासवर्ड छिपाता है, और कभी सामग्री प्रिंट नहीं करता। `hirehunt` प्रॉक्सी ऑप्शन नहीं देता, इसलिए जब प्रोफ़ाइल में एक सेट होता है तो Sweepy चेतावनी लॉग करता है।
- **कैश चालू हालत में शुरू होता है।** वही क्वेरी उन्हीं इंजन और सेटिंग्स के साथ एक घंटे तक पिछले नतीजे लौटाती है। इसे `cache.enabled: false` से साफ़ करें, या `ttl_seconds` छोटा करें।
- **टाइमआउट सीमा पर रुकते हैं।** Python ऐसे थ्रेड को रोक नहीं सकता जो पहले से लाइब्रेरी कॉल में ब्लॉक है। Sweepy इंतज़ार करना छोड़कर आगे बढ़ता है, और हर लाइब्रेरी नीचे अपने HTTP टाइमआउट लागू करती है।
- **सर्किट ब्रेकर फेल होते इंजन को छोड़ देता है।** लगातार पाँच फेल्योर के बाद Sweepy उस इंजन को 30 सेकंड तक कॉल करना बंद कर देता है और उसे `skipped_sources` में रिपोर्ट करता है।

### <a name="reported-postings"></a>रिपोर्ट की गई पोस्टिंग

Sweepy हर रिपोर्ट की गई पोस्टिंग दर्ज करता है और अगले स्वीप में वही पोस्टिंग छोड़ देता है। Sweepy रिकॉर्ड को `~/.sweepy/history.db` में रखता है, प्रोफ़ाइल के हिसाब से सीमित। इसे कहीं और रखने के लिए `SWEEPY_HISTORY_PATH` सेट करें। विज़ार्ड की **Sweep Settings** स्क्रीन चालू/बंद स्विच और रिटेंशन विंडो दिखाती है।

```yaml
history:
  enabled: true
  retention_days: 4   # 0 reports every posting on every run
  match: url+role     # url (strict) or url+role (default)
  path: null          # null uses ~/.sweepy/history.db
```

- **रिटेंशन एक दोबारा-रिपोर्ट कैडेंस है।** Sweepy पोस्टिंग को `retention_days` बीतने तक दबाए रखता है, फिर उसे दोबारा रिपोर्ट करता है। लगातार लाइव लिस्टिंग ज़्यादा से ज़्यादा हर चार दिन में लौटती है।
- **मैचिंग डिफ़ॉल्ट रूप से उदार है।** Sweepy ट्रैकिंग पैरामीटर और फ़्रैगमेंट हटाने के बाद कैनोनिकल URL की तुलना करता है। फिर यह नॉर्मलाइज़ टाइटल, कंपनी, और लोकेशन पर लौटता है, इसलिए दूसरे बोर्ड पर दोबारा पोस्ट की गई भूमिका वही भूमिका गिनी जाती है। कैनोनिकल URL मैच अनिवार्य करने के लिए `match: url` सेट करें।
- **सिर्फ लाइव पोस्टिंग गिनी जाती हैं।** पोस्टिंग इतिहास में तभी आती है जब उसका URL वैलिडेशन पास कर लेता है। एक्सपायर लिंक कभी अदृश्य नहीं होते।
- **MCP कॉलर को वही डिफ़ॉल्ट मिलता है।** `run_sweep` `previously_seen_count` और `new_count` रिपोर्ट करता है। पहले की पोस्टिंग देखने के लिए `include_seen=true` पास करें, या उन्हें भुलाने के लिए `clear_history` कॉल करें। `create_profile` `history_config` स्वीकार करता है।

### <a name="adding-another-engine"></a>एक और इंजन जोड़ना

1. `engine/adapters/<name>_adapter.py` बनाएँ और `ScraperAdapter` को सबक्लास करें।
2. `name`, तीन `supports_*` फ़्लैग, `default_concurrency`, और `library` सेट करें।
3. कॉन्फ़िग जाँचने के लिए `preflight()` और DataFrame लौटाने के लिए `scrape()` लिखें।
4. इसे `engine/adapters/__init__.py` में रजिस्टर करें।
5. इसे `engine/engines.py` में बताएँ ताकि विज़ार्ड उसे दिखा और इंस्टॉल कर सके।
6. `engine/sweep_config.py` में कॉन्फ़िग ब्लॉक जोड़ें और `_ENGINE_PROMPTS` के लिए `engine/config.py` में प्रॉम्प्ट जोड़ें।
7. पैकेज को `requirements-engines.txt` और pyproject extras में जोड़ें।
8. एडाप्टर को अलग से टेस्ट करें, फिर स्वीप के दौरान उसे अकेले चालू करें।

ऑर्केस्ट्रेटर बाकी संभालता है। यह नाम से डिस्पैच करता है और टाइमआउट लागू करता है। जो भी फ़्रेम लौटता है उसे नॉर्मलाइज़ कर दिया जाता है।

## <a name="connect-to-antigravity"></a>Antigravity से कनेक्ट करें

Sweepy दो हिस्सों के ज़रिए Antigravity डेस्कटॉप ऐप में चलता है। MCP सर्वर खोज उपकरण देता है, और `/sweepy` स्किल चैट शॉर्टकट जोड़ती है।

**एजेंट से कहें।** Antigravity खोलें, चैट शुरू करें, और यह संदेश भेजें:

> मेरे लिए Sweepy सेट करें। `python <PATH_TO_SWEEPY>/server.py` पर चलने वाला स्थानीय MCP सर्वर पंजीकृत करें, और `<PATH_TO_SWEEPY>/skills/sweepy` से स्किल इंस्टॉल करें।

Antigravity कॉन्फ़िगरेशन लिखता है और स्किल फ़ाइलें आपके सिस्टम में जोड़ देता है।

**इसे हाथ से सेट करें।** इन चरणों को क्रम से पूरा करें।

1. **MCP सर्वर जोड़ें।** **सेटिंग्स** (गियर आइकन) > **MCP Servers** खोलें और `sweepy` नाम का सर्वर जोड़ें। कमांड में `python` रखें और आर्ग्युमेंट में `["<PATH_TO_SWEEPY>/server.py"]`।
2. **स्किल इंस्टॉल करें।** अपना स्किल फ़ोल्डर खोलें: Windows पर `%USERPROFILE%\.gemini\config\skills`, या macOS पर `~/.gemini/config/skills`। `sweepy` फ़ोल्डर को `skills/sweepy` से उस डायरेक्टरी में कॉपी करें, फिर Antigravity रीस्टार्ट करें।
3. **खोज चलाएँ।** चैट में `/sweepy` टाइप करें। सादे शब्दों में माँगने के लिए यह अनुरोध भेजें: *"`C:/path/to/resume.pdf` पर रखे मेरे रिज़्यूमे से दूरस्थ तकनीकी लेखक भूमिकाओं के लिए प्रोफ़ाइल बनाएँ और मेरी पहली खोज चलाएँ।"*

Antigravity किसी भी दूसरे होस्ट की तरह वही MCP उपकरण कॉल करता है। [MCP एकीकरण](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration) पेज Claude Desktop, VS Code और उपकरणों की पूरी सूची समझाता है।

## <a name="agent-judgment"></a>एजेंट जजमेंट

Sweepy पोस्टिंग को साझा शब्दावली से स्कोर करता है, और वह स्कोरिंग किसी मॉडल को कॉल नहीं करती और नेटवर्क इस्तेमाल नहीं करती। वही इनपुट वही स्कोर देते हैं, जो शब्दों को मापता है, फ़िट को नहीं। MCP सर्वर एजेंट मूल्यांकन को अपेक्षित रास्ता मानता है।

`run_sweep` किसी मॉडल को कॉल नहीं करता। यह `assessment_mode: "agent"`, `assessment_required: true`, और `assessed_count: 0` लौटाता है। वर्कफ़्लो `get_jobs`, रिज़्यूमे के सामने हर भूमिका का स्वतंत्र मूल्यांकन, `submit_judgments`, और `render_report` के साथ आगे बढ़ता है। 24 भूमिकाओं का मूल्यांकन एक कॉल में रखने के लिए हर judgment एक ही `judgments` सूची में दें। मूल्यांकित कार्ड `NN% MATCH` दिखाते हैं। बिना मूल्यांकन वाले कार्ड `NN% KEYWORD OVERLAP` रखते हैं।

`get_jobs` हर रिज़्यूमे ट्रैक के पार्स किए टेक्स्ट के साथ `resume_documents` लौटाता है। उस टेक्स्ट को जज करें, प्रोफ़ाइल के `must_have_skills` और `synonyms` को नहीं, जो सिर्फ नियतिवादी keyword पास को फ़ीड करते हैं। डॉक्यूमेंट को वैसे पढ़ें जैसे रिक्रूटर पढ़ता है: ट्रांसफ़रेबल स्किल्स, हर बुलेट के पीछे का दायरा और अनुभव-स्तर, डोमेन, टूल, और जो नतीजे वह साबित करता है। फिर उसे वैसे स्कोर करें जैसे पोस्टिंग का applicant tracking system पार्स करता है। स्टैंडर्ड Experience या Skills सेक्शन में पार्सर को मिला शब्द सबूत गिना जाता है। वही शब्द किसी टेबल, हेडर, फ़ुटर, इमेज, या दो-कॉलम साइडबार के अंदर शायद किसी व्यक्ति तक पहुँचे ही नहीं, इसलिए उसका वज़न कम है। जब अप्लाई URL से पता चलता है तो Sweepy ATS फ़ैमिली का नाम बताता है, और judgment दर्ज करता है कि पार्सर क्या खो देगा।

`match_pct` योग्यता मापता है, इसलिए रोज़गार की लॉजिस्टिक्स उससे बाहर रहती हैं। पार्ट-टाइम घंटे, कॉन्ट्रैक्ट स्थिति, और लोकेशन `concerns` में जाते हैं। जो भूमिका उम्मीदवार कर सकता है उसके अंक सिर्फ तब घटते हैं जब स्किल्स या अनुभव पोस्टिंग की बताई ज़रूरतों से मेल न खाएँ। तब रैंकिंग उपलब्धता के बजाय फ़िट मापती है।

मामले के दोनों पक्ष देखें। `alignment` मुख्य बात बताता है, यानी सबसे मज़बूत सबूत कि उम्मीदवार फ़िट है। `concerns` बताता है कि उम्मीदवार के ख़िलाफ़ क्या है। उदाहरण के लिए, छूटी योग्यता, टेन्योर का अंतर, पार्ट-टाइम घंटे, कॉन्ट्रैक्ट अवधि, ऐसी लोकेशन जिसके लिए शिफ्ट करना पड़े, या फ़्लोर से नीचे पे। रिपोर्ट यह जोड़ी ज़रूरतों वाली पंक्ति के नीचे एक लाइन में प्रिंट करती है, और CSV में `concerns` कॉलम जुड़ता है। सिर्फ keyword वाला रन `concerns` उन पोस्टिंग keywords से भरता है जो रिज़्यूमे में नहीं मिलते।

`submit_judgments` `portfolio_highlight` भी लेता है। उस पोस्टिंग के पोर्टफ़ोलियो पीस दें, और कार्ड उन्हें **Highlight** के रूप में प्रिंट करता है। जिस कार्ड में कोई भेजा हुआ highlight नहीं है वह Sweepy के खोजे पीस दिखाता है।

## <a name="portfolio-support"></a>पोर्टफ़ोलियो सपोर्ट

Sweepy पोर्टफ़ोलियो को हर स्वीप में एक बार पढ़ता है और उसके पीस हर कार्ड पर दिखाता है। यह प्रोफ़ाइल बनाने से पहले पोर्टफ़ोलियो जुटाता है। इसे ऑनलाइन URL या लोकल `.pdf`, `.docx`, `.md`, `.txt`, या `.html` फ़ाइल दें। जब आप एक से ज़्यादा भूमिका परिवारों को टारगेट करते हैं तो हर रिज़्यूमे ट्रैक के लिए एक एंट्री दें।

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

Sweepy ऑनलाइन पोर्टफ़ोलियो की हेडिंग और लिंक पढ़ने के लिए उसे फ़ेच करता है। जब कोई पेज रिक्वेस्ट ब्लॉक करता है, तो कार्ड लिंक रखता है और पीस सूची छोड़ देता है। PDF कार्ड पोर्टफ़ोलियो और उसके पीस दिखाता है। CSV और JSON एक्सपोर्ट `portfolio_url`, `portfolio_pieces`, और `portfolio_highlight` जोड़ते हैं।

सेव की गई प्रोफ़ाइल से पोर्टफ़ोलियो जोड़ने के लिए MCP से `set_portfolio` कॉल करें या विज़ार्ड का पोर्टफ़ोलियो स्टेप भरें। हेडलेस सेटअप `--portfolio` और `--portfolio-track` स्वीकार करता है।

`render_report` क्लोज़िंग स्ट्रैटेजी बॉक्स के लिए `playbook` आर्ग्युमेंट लेता है। सादा गद्य लिखें। Sweepy ampersand एस्केप करता है और नई पंक्तियों को लाइन ब्रेक में बदलता है। `**bold**` बोल्ड टेक्स्ट के रूप में रेंडर होता है, और एंगल ब्रैकेट सादा टेक्स्ट बन जाते हैं। Sweepy playbook को सेशन के साथ रखता है, और बाद का render जनरेट किए गए वाले के बजाय उसे दोबारा इस्तेमाल करता है। नया स्वीप शुरू करने पर वह साफ़ हो जाता है।

`agent` मोड में `render_report` मिली-जुली रिपोर्ट बनाने से मना कर देता है। यह बिना मूल्यांकन वाले जॉब ids की सूची के साथ त्रुटि लौटाता है। असिस्टेंट वह सूची पढ़ता है और छूटे ids के लिए judgments भेजता है। सिर्फ keyword रिपोर्ट चाहने वाली प्रोफ़ाइल `report.assessment: "keyword"` सेट करती हैं। कमांड-लाइन रन भी keyword overlap रिपोर्ट करता है, क्योंकि कोई एजेंट judgments नहीं देता। `SWEEPY_REQUIRE_JUDGMENTS=1` सेट करें जब गेट हर प्रोफ़ाइल पर और `export_report` पर भी लागू होना चाहिए।

लाइव स्वीप बोर्ड एक मिनट या ज़्यादा स्क्रैप करता है। MCP सर्वर इसे बैकग्राउंड में चलाता है। `run_sweep` ज़्यादा से ज़्यादा 45 सेकंड रुकता है और फिर `sweep_status: "running"` के साथ `job_id` लौटाता है। जब तक `get_sweep_status` `completed` न बताए, पोल करें। क्लाइंट डिस्कनेक्ट होने पर भी स्वीप चलता रहता है। कम टूल टाइमआउट वाले होस्ट के लिए इंतज़ार घटाने हेतु `SWEEPY_MCP_WAIT_SECONDS` सेट करें।

- MCP से बनी प्रोफ़ाइल बिल्ट-इन इंजन और वे इंस्टॉल किए गए ऑप्शनल इंजन इस्तेमाल करती हैं जो अपने डिफ़ॉल्ट कॉन्फ़िगरेशन चेक पास करते हैं।
- इंजन स्पष्ट रूप से चुनने के लिए `sources_config` दें।
- OpenRoles को हर कंपनी के लिए एक slug चाहिए।
- Apify को स्पष्ट opt-in चाहिए क्योंकि इससे शुल्क लग सकता है।

असिस्टेंट अपने सर्च टूल से नतीजे जाँच सकता है और कमियाँ भर सकता है। उसे छोड़े गए सोर्स और पोस्टिंग नियोक्ता के करियर पेजों के सामने जाँचने चाहिए। उसे सत्यापित छूटें जोड़नी चाहिए और जिन लिस्टिंग तक पहुँच नहीं है उन्हें unverified लेबल करना चाहिए। जब वह पूरी कवरेज पक्की न कर सके तो उसे यह बताना चाहिए।

सेटअप स्टेप के लिए [MCP इंटीग्रेशन](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration) पढ़ें।

हर MCP टूल read-only, destructive, idempotent, और open-world हिंट प्रकाशित करता है। संगत होस्ट टूल कॉल करने से पहले वे हिंट पढ़ते हैं।

## <a name="before-you-upload-your-resume"></a>रिज़्यूमे अपलोड करने से पहले

आपका लेआउट तय करता है कि Sweepy कितना टेक्स्ट पढ़ सकता है। दो-कॉलम डिज़ाइन, टेबल, या स्कैन किया पेज इंजन के पढ़े टेक्स्ट को उलझा देता है और आपके स्कोर घटा देता है। असली टेक्स्ट का एक साफ़ कॉलम सबसे भरोसेमंद तरीके से निकलता है, और applicant tracking systems उसे उसी तरह पढ़ते हैं।

अपने पहले स्वीप से पहले [रिज़्यूमे फ़ॉर्मैटिंग टिप्स](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips) पढ़ें।

## <a name="documentation"></a>डॉक्यूमेंटेशन

### <a name="getting-started"></a>शुरुआत करना

- [परिचय](https://pvega62.github.io/software/docs/sweepy/intro)
- [इंस्टॉलेशन](https://pvega62.github.io/software/docs/sweepy/installation)
- [कॉन्फ़िगरेशन](https://pvega62.github.io/software/docs/sweepy/setup)
- [अपना पहला स्वीप चलाना](https://pvega62.github.io/software/docs/sweepy/first-sweep)
- [अपने नतीजे समझना](https://pvega62.github.io/software/docs/sweepy/understanding-results)

### <a name="resumes-and-match-scores"></a>रिज़्यूमे और मैच स्कोर

- [रिज़्यूमे फ़ॉर्मैटिंग टिप्स](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)
- [स्कोरिंग और सीमाएँ](https://pvega62.github.io/software/docs/sweepy/guides/scoring-and-limits)

### <a name="command-and-configuration-reference"></a>कमांड और कॉन्फ़िगरेशन संदर्भ

- [कमांड और फ़्लैग](https://pvega62.github.io/software/docs/sweepy/reference/cli-reference)
- [कॉन्फ़िगरेशन संदर्भ](https://pvega62.github.io/software/docs/sweepy/reference/configuration-reference)
- [जॉब सोर्स और प्लेटफ़ॉर्म](https://pvega62.github.io/software/docs/sweepy/reference/sources-and-platforms)
- [MCP इंटीग्रेशन](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)
- [MCP टूल संदर्भ](https://pvega62.github.io/software/docs/sweepy/reference/mcp-tool-reference)
- [डेवलपर संदर्भ](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## <a name="legal-and-responsible-use"></a>कानूनी और ज़िम्मेदार उपयोग

Sweepy सार्वजनिक जॉब बोर्ड और जॉब-बोर्ड APIs स्क्रैप करता है। स्क्रैपिंग कुछ प्लेटफ़ॉर्म की सेवा शर्तों का उल्लंघन कर सकती है। टूल पर भरोसा करने से पहले वे शर्तें पढ़ें।

- इसे **निजी जॉब सर्च** के लिए इस्तेमाल करें। थोक संग्रह या पुनर्वितरण के लिए इसका उपयोग न करें।
- रेट लिमिट का पालन करें। Sweepy विनम्र User-Agent और रिक्वेस्ट के बीच छोटा डिले भेजता है। `SWEEPY_SOURCE_DELAY` एनवायरनमेंट वेरिएबल से डिले बढ़ाएँ।
- Sweepy कानूनी सलाह नहीं देता।

स्क्रैपिंग [`python-jobspy`](https://github.com/Bunsly/JobSpy) से चलती है और, जब आप उन्हें इंस्टॉल करते हैं, [`hirehunt`](https://pypi.org/project/hirehunt/), [`openroles`](https://pypi.org/project/openroles/), [`jobdrop`](https://pypi.org/project/jobdrop/), और [Apify](https://apify.com/) से भी। हर प्रोजेक्ट अपने उपयोग नोट्स प्रकाशित करता है। Google Jobs, LinkedIn, Indeed, और Glassdoor की स्क्रैपिंग उन प्लेटफ़ॉर्म की सेवा शर्तों का उल्लंघन कर सकती है। Apify रिक्वेस्ट को मैनेज्ड सर्विस पर ले जाता है। इससे कानूनी जोखिम नहीं बदलता।

## <a name="license"></a>लाइसेंस

Sweepy [MIT License](../LICENSE) के तहत रिलीज़ होता है।
