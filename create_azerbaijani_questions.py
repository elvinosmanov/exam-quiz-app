import sqlite3
import os

def create_questions():
    db_path = os.path.join(os.path.dirname(__file__), 'quiz_app.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First, create exams for each topic
    topics = {
        "Fizika": "Fizika sahəsində ümumi biliklərin yoxlanması",
        "Astronomiya": "Astronomiya və kosmik elmlərlə bağlı suallar",
        "Programlaşdırma": "Proqramlaşdırma və informatika üzrə suallar",
        "Məntiq": "Məntiqi düşüncə və استدلال qabiliyyətinin yoxlanması",
        "Peyk mühəndisliyi": "Peyk texnologiyaları və kosmik mühəndislik",
        "Telekomunikasiya": "Telekomunikasiya və rabitə texnologiyaları"
    }

    exam_ids = {}
    for topic_name, description in topics.items():
        cursor.execute("""
            INSERT INTO exams (title, description, duration_minutes, passing_score,
                             randomize_questions, show_results, is_active, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (topic_name, description, 60, 50.0, 0, 1, 1, 1))
        exam_ids[topic_name] = cursor.lastrowid

    # Questions data structure: [topic, question_text, question_type, correct_answer, points, options/explanation]
    questions_data = []

    # ========== FİZİKA (20 questions) ==========
    fizika_questions = [
        ("Fizika", "Işığın vakuumda sürəti nə qədərdir?", "multiple_choice", "300,000 km/s", 2,
         [("150,000 km/s", False), ("300,000 km/s", True), ("450,000 km/s", False), ("600,000 km/s", False)]),

        ("Fizika", "Newton-un birinci qanunu nəyi ifadə edir?", "multiple_choice", "Ətalət qanunu", 2,
         [("Ətalət qanunu", True), ("Qüvvə qanunu", False), ("Təsir-qarşı təsir", False), ("Cazibə qanunu", False)]),

        ("Fizika", "Elektrik cərəyanının vahidi hansıdır?", "multiple_choice", "Amper", 1,
         [("Volt", False), ("Amper", True), ("Om", False), ("Vatt", False)]),

        ("Fizika", "Enerji saxlanma qanununa görə, enerji yaradıla və ya məhv edilə bilər.", "true_false", "False", 1, None),

        ("Fizika", "Kvant mexanikasının əsasını qoyan alim kimdir?", "short_answer", "Max Planck", 2,
         "Max Planck kvant nəzəriyyəsinin əsasını qoymuşdur"),

        ("Fizika", "Termodinamikanın ikinci qanununu izah edin və onun praktik tətbiqlərini göstərin.", "essay", None, 5,
         "Cavabda entropiya, istiliyin ötürülməsi və termodinamik proseslər haqqında məlumat olmalıdır"),

        ("Fizika", "Atom nüvəsi hansı hissəciklərdən ibarətdir?", "multiple_choice", "Proton və neytron", 2,
         [("Elektron və proton", False), ("Proton və neytron", True), ("Neytron və elektron", False), ("Yalnız protonlar", False)]),

        ("Fizika", "Səs dalğaları vakuumda yayıla bilər.", "true_false", "False", 1, None),

        ("Fizika", "Ohm qanununu yazın.", "short_answer", "V = I × R", 2,
         "Gərginlik = Cərəyan × Müqavimət"),

        ("Fizika", "Eynşteynin xüsusi nisbilik nəzəriyyəsinin əsas prinsiplərini izah edin.", "essay", None, 5,
         "Cavabda işıq sürətinin sabitliyi və zaman-məkan münasibətləri izah edilməlidir"),

        ("Fizika", "Qravitasiya təcilinin Yer səthində orta qiyməti nə qədərdir?", "multiple_choice", "9.8 m/s²", 2,
         [("8.8 m/s²", False), ("9.8 m/s²", True), ("10.8 m/s²", False), ("11.8 m/s²", False)]),

        ("Fizika", "Maqnit sahəsinin vahidi Tesla ilə ölçülür.", "true_false", "True", 1, None),

        ("Fizika", "Fotoelektrik effekti nədir?", "short_answer", "Işığın metaldan elektron çıxarması", 2,
         "Işığın metallara təsiri nəticəsində elektronların sərbəst buraxılması"),

        ("Fizika", "Dalğa-hissəcik dualizmi anlayışını izah edin və misallar gətirin.", "essay", None, 5,
         "Cavabda kvant mexanikası, işıq və elektronların xassələri haqqında məlumat olmalıdır"),

        ("Fizika", "Alternativ cərəyan (AC) hansı tezliklə dəyişir (Azərbaycanda)?", "multiple_choice", "50 Hz", 1,
         [("50 Hz", True), ("60 Hz", False), ("100 Hz", False), ("120 Hz", False)]),

        ("Fizika", "Sürtünmə qüvvəsi həmişə hərəkətə əks istiqamətdə təsir edir.", "true_false", "True", 1, None),

        ("Fizika", "Planck sabitinin qiyməti nə qədərdir?", "short_answer", "6.626 × 10⁻³⁴ J·s", 2,
         "Plank sabiti kvant mexanikasında fundamental sabittir"),

        ("Fizika", "Nüvə parçalanması və sintezi proseslərini müqayisə edin və enerji istehsalındakı rollarını izah edin.", "essay", None, 5,
         "Cavabda fisiya, füziya prosesləri və onların tətbiqləri izah edilməlidir"),

        ("Fizika", "Daxili enerji nədir?", "multiple_choice", "Sistemin bütün hissəciklərinin kinetik və potensial enerjilərinin cəmi", 2,
         [("Yalnız kinetik enerji", False), ("Yalnız potensial enerji", False), ("Sistemin bütün hissəciklərinin kinetik və potensial enerjilərinin cəmi", True), ("Xarici qüvvələrin işi", False)]),

        ("Fizika", "Heisenberg-in qeyri-müəyyənlik prinsipi kvant mexanikasının əsas prinsiplərindən biridir.", "true_false", "True", 1, None),
    ]

    # ========== ASTRONOMİYA (20 questions) ==========
    astronomiya_questions = [
        ("Astronomiya", "Günəş sisteminin ən böyük planeti hansıdır?", "multiple_choice", "Yupiter", 1,
         [("Mars", False), ("Yupiter", True), ("Saturn", False), ("Neptun", False)]),

        ("Astronomiya", "Ulduzların əmələ gəlməsi hansı proseslə başlayır?", "multiple_choice", "Qravitasiya yığılması", 2,
         [("Qravitasiya yığılması", True), ("Nüvə sintezi", False), ("Maqnit sahəsi", False), ("Kosmik şüalanma", False)]),

        ("Astronomiya", "Ay Yerin təbii peykidir.", "true_false", "True", 1, None),

        ("Astronomiya", "Qara dəlik nədir?", "short_answer", "Cazibə qüvvəsi çox güclü olan kosmos obyekti", 2,
         "Işığın belə qaça bilməyəcəyi qədər güclü qravitasiya sahəsinə malik obyekt"),

        ("Astronomiya", "Böyük Partlayış (Big Bang) nəzəriyyəsini izah edin və onun əsas sübutlarını göstərin.", "essay", None, 5,
         "Cavabda kainatın genişlənməsi, mikrodalğalı fon şüalanması haqqında məlumat olmalıdır"),

        ("Astronomiya", "Işıq ili nəyi ölçür?", "multiple_choice", "Məsafə", 2,
         [("Zaman", False), ("Məsafə", True), ("Sürət", False), ("Enerji", False)]),

        ("Astronomiya", "Mars planetində su olub.", "true_false", "True", 1, None),

        ("Astronomiya", "Ən yaxın ulduz sisteminin adı nədir?", "short_answer", "Alfa Centauri", 2,
         "Günəşdən sonra bizə ən yaxın ulduz sistemi"),

        ("Astronomiya", "Galaktika növlərini təsvir edin və Süd Yolu qalaktikasının xüsusiyyətlərini izah edin.", "essay", None, 5,
         "Cavabda spiral, elliptik və nizamsız qalaktikalar haqqında məlumat olmalıdır"),

        ("Astronomiya", "Günəş sistemində neçə planet var?", "multiple_choice", "8", 1,
         [("7", False), ("8", True), ("9", False), ("10", False)]),

        ("Astronomiya", "Venera planetinin atmosferi əsasən karbon dioksiddən ibarətdir.", "true_false", "True", 1, None),

        ("Astronomiya", "Supernovə partlayışı nədir?", "short_answer", "Ulduzun partlayaraq məhv olması", 2,
         "Böyük ulduzların həyat dövrünün sonunda baş verən güclü partlayış"),

        ("Astronomiya", "Qaranlıq maddə və qaranlıq enerjinin kainatdakı rolunu izah edin.", "essay", None, 5,
         "Cavabda kainatın tərkibi və genişlənməsi haqqında məlumat olmalıdır"),

        ("Astronomiya", "Yer öz oxu ətrafında neçə saatda tam dövr edir?", "multiple_choice", "24 saat", 1,
         [("12 saat", False), ("24 saat", True), ("48 saat", False), ("36 saat", False)]),

        ("Astronomiya", "Pluton artıq planet sayılmır.", "true_false", "True", 1, None),

        ("Astronomiya", "Ekzoplanetlər necə aşkar edilir?", "short_answer", "Tranzit və radial sürət metodları", 2,
         "Ulduzun parlaqlığının dəyişməsi və ya ulduzun hərəkətinin müşahidəsi ilə"),

        ("Astronomiya", "Ulduzların həyat dövrünü və onların təkamülünü izah edin.", "essay", None, 5,
         "Cavabda ulduzların əmələ gəlməsi, əsas ardıcıllıq, qırmızı nəhəng və son mərhələlər izah edilməlidir"),

        ("Astronomiya", "Günəşdə hansı proses enerji istehsal edir?", "multiple_choice", "Nüvə sintezi", 2,
         [("Nüvə parçalanması", False), ("Nüvə sintezi", True), ("Kimyəvi reaksiya", False), ("Qravitasiya sıxılması", False)]),

        ("Astronomiya", "Kometa və asteroidlər eyni şeydir.", "true_false", "False", 1, None),

        ("Astronomiya", "Habbl teleskopu nə vaxt kosmosa göndərilmişdir?", "short_answer", "1990", 2,
         "Hubble Space Telescope 1990-cı ildə orbitə çıxarılmışdır"),
    ]

    # ========== PROQRAMLAŞDIRMA (20 questions) ==========
    programlasdirma_questions = [
        ("Programlaşdırma", "Python-da dəyişən elan etmək üçün hansı açar sözdən istifadə olunur?", "multiple_choice", "Heç biri, birbaşa təyin edilir", 2,
         [("var", False), ("let", False), ("define", False), ("Heç biri, birbaşa təyin edilir", True)]),

        ("Programlaşdırma", "Obyekt yönümlü proqramlaşdırmada OOP-nin 4 əsas prinsipi hansılardır?", "multiple_choice", "Enkapsulasiya, İrs, Polimorfizm, Abstraksiya", 3,
         [("Enkapsulasiya, İrs, Polimorfizm, Abstraksiya", True), ("Döngü, Şərt, Funksiya, Sinif", False), ("Array, List, Set, Map", False), ("Input, Output, Process, Store", False)]),

        ("Programlaşdırma", "JavaScript interpretasiya olunan dildir.", "true_false", "True", 1, None),

        ("Programlaşdırma", "SQL-də JOIN əməliyyatı nə üçün istifadə olunur?", "short_answer", "Cədvəlləri birləşdirmək", 2,
         "İki və ya daha çox cədvəldəki məlumatları əlaqələndirmək üçün"),

        ("Programlaşdırma", "Alqoritm mürəkkəbliyi anlayışını izah edin və Big O notasiyasının əhəmiyyətini göstərin.", "essay", None, 5,
         "Cavabda O(1), O(n), O(log n), O(n²) kimi nümunələr və onların praktik əhəmiyyəti izah edilməlidir"),

        ("Programlaşdırma", "Git-də hansı əmr dəyişiklikləri commit edir?", "multiple_choice", "git commit", 1,
         [("git push", False), ("git add", False), ("git commit", True), ("git merge", False)]),

        ("Programlaşdırma", "Array və Linked List eyni məlumat strukturlarıdır.", "true_false", "False", 1, None),

        ("Programlaşdırma", "REST API nədir?", "short_answer", "RESTful arxitektura ilə qurulmuş API", 2,
         "HTTP protokolu üzərindən məlumat mübadiləsi üçün arxitektur üslub"),

        ("Programlaşdırma", "Relational və NoSQL verilənlər bazalarını müqayisə edin və hər birinin üstünlüklərini izah edin.", "essay", None, 5,
         "Cavabda SQL və NoSQL verilənlər bazalarının strukturu, skalanma və istifadə sahələri izah edilməlidir"),

        ("Programlaşdırma", "Hansı dil aşağı səviyyəli dildir?", "multiple_choice", "Assembly", 2,
         [("Python", False), ("JavaScript", False), ("Assembly", True), ("Ruby", False)]),

        ("Programlaşdırma", "Rekursiv funksiya özünü çağıran funksiyadır.", "true_false", "True", 1, None),

        ("Programlaşdırma", "Stack və Queue məlumat strukturlarının fərqi nədir?", "short_answer", "LIFO və FIFO prinsipləri", 2,
         "Stack-da LIFO (Last In First Out), Queue-da FIFO (First In First Out) prinsipi işləyir"),

        ("Programlaşdırma", "Mikroservis arxitekturasını izah edin və monolit arxitektura ilə müqayisə edin.", "essay", None, 5,
         "Cavabda servislərin ayrılması, skalanma, deployment və üstünlük/çatışmazlıqlar izah edilməlidir"),

        ("Programlaşdırma", "Docker nə üçün istifadə olunur?", "multiple_choice", "Konteynerləşdirmə", 2,
         [("Versiya idarəetməsi", False), ("Konteynerləşdirmə", True), ("Verilənlər bazası", False), ("Şifrələmə", False)]),

        ("Programlaşdırma", "Machine Learning süni intellektin bir sahəsidir.", "true_false", "True", 1, None),

        ("Programlaşdırma", "SOLID prinsipləri nədir?", "short_answer", "Obyekt yönümlü dizayn prinsipləri", 2,
         "Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion"),

        ("Programlaşdırma", "DevOps metodologiyasını və CI/CD proseslərini izah edin.", "essay", None, 5,
         "Cavabda avtomatlaşdırma, continuous integration, continuous deployment və DevOps mədəniyyəti izah edilməlidir"),

        ("Programlaşdırma", "Blockchain texnologiyasının əsas prinsipi nədir?", "multiple_choice", "Paylanmış reyestr", 2,
         [("Mərkəzləşdirilmiş server", False), ("Paylanmış reyestr", True), ("Bulud yaddaşı", False), ("Kvant hesablama", False)]),

        ("Programlaşdırma", "API və SDK eyni anlayışlardır.", "true_false", "False", 1, None),

        ("Programlaşdırma", "Agile metodologiyasının əsas prinsiplərindən biri nədir?", "short_answer", "İterativ inkişaf", 2,
         "Davamlı təkmilləşdirmə, tez-tez çatdırma və müştəri əməkdaşlığı"),
    ]

    # ========== MƏNTİQ (20 questions) ==========
    mentiq_questions = [
        ("Məntiq", "Deduksiya və induksiya arasında əsas fərq nədir?", "multiple_choice", "Deduksiya ümumdən xüsusiyə, induksiya xüsusidən ümumiyə gedir", 2,
         [("Deduksiya ümumdən xüsusiyə, induksiya xüsusidən ümumiyə gedir", True), ("Hər ikisi eynidir", False), ("Deduksiya yalnız riyaziyyatda istifadə olunur", False), ("İnduksiya məntiqi deyil", False)]),

        ("Məntiq", "Əgər A → B doğrudursa və A doğrudursa, onda B də doğrudur.", "true_false", "True", 1, None),

        ("Məntiq", "Modus Ponens nədir?", "short_answer", "Təsdiq edici məntiqi çıxarış qaydası", 2,
         "Əgər A onda B, A doğrudur, deməli B doğrudur"),

        ("Məntiq", "Formal məntiq və qeyri-formal məntiq arasındakı fərqi izah edin və hər birinin tətbiq sahələrini göstərin.", "essay", None, 5,
         "Cavabda formal sistemlər, simvolik məntiq və təbii dil məntiqi izah edilməlidir"),

        ("Məntiq", "Sillogizm nədir?", "multiple_choice", "İki müqəddiməli məntiqi mülahizə", 2,
         [("Riyazi tənlik", False), ("İki müqəddiməli məntiqi mülahizə", True), ("Elmi nəzəriyyə", False), ("Fəlsəfi konsepsiya", False)]),

        ("Məntiq", "\"Bütün insanlar ölümlüdür\" ifadəsi universal mənfi hökümdür.", "true_false", "False", 1, None),

        ("Məntiq", "Tautologiya nədir?", "short_answer", "Həmişə doğru olan məntiq ifadəsi", 2,
         "Məntiqi cəhətdən həmişə doğru olan və ya özü-özünə doğru olan ifadə"),

        ("Məntiq", "Boolean cəbrini və onun rəqəmsal dövrələrdə tətbiqini izah edin.", "essay", None, 5,
         "Cavabda AND, OR, NOT əməliyyatları və rəqəmsal sistemlərdəki rolu izah edilməlidir"),

        ("Məntiq", "De Morgan qanunları nəyi ifadə edir?", "multiple_choice", "NOT(A AND B) = NOT A OR NOT B", 2,
         [("A + B = B + A", False), ("NOT(A AND B) = NOT A OR NOT B", True), ("A × B = B × A", False), ("A - B ≠ B - A", False)]),

        ("Məntiq", "Paradoks özü-özünə ziddiyyətli ifadədir.", "true_false", "True", 1, None),

        ("Məntiq", "Kontrapozisiya qanunu nədir?", "short_answer", "A→B = ¬B→¬A", 2,
         "Əgər A onda B, bu ¬B onda ¬A ilə eynidir"),

        ("Məntiq", "Predikat məntiqini izah edin və onun propozisional məntiqə nisbətən üstünlüklərini göstərin.", "essay", None, 5,
         "Cavabda kvantorlar, predikatlar və ifadə gücü haqqında məlumat olmalıdır"),

        ("Məntiq", "Hansı məntiqi operator birləşdirmə əməliyyatını ifadə edir?", "multiple_choice", "AND (∧)", 1,
         [("AND (∧)", True), ("OR (∨)", False), ("NOT (¬)", False), ("XOR (⊕)", False)]),

        ("Məntiq", "Məntiqi tutarlılıq və tamlıq eyni anlayışlardır.", "true_false", "False", 1, None),

        ("Məntiq", "Reductio ad absurdum metodu nədir?", "short_answer", "Absurdluğa gətirilməklə sübut", 2,
         "Əks tezisi qəbul edib ona gətirilən ziddiyyətlə əsl tezisi sübut etmə"),

        ("Məntiq", "Modal məntiq və onun zəruriyyət/mümkünlük konsepsiyalarını izah edin.", "essay", None, 5,
         "Cavabda mümkün dünyalar, zəruriyyət və mümkünlük operatorları izah edilməlidir"),

        ("Məntiq", "Doğruluk cədvəli nə üçün istifadə olunur?", "multiple_choice", "Məntiqi ifadələrin doğruluğunu yoxlamaq", 2,
         [("Riyazi hesablamalar", False), ("Məntiqi ifadələrin doğruluğunu yoxlamaq", True), ("Qrammatik təhlil", False), ("Statistik analiz", False)]),

        ("Məntiq", "Eksklyuziv OR (XOR) yalnız hər iki daxil fərqli olduqda doğru verir.", "true_false", "True", 1, None),

        ("Məntiq", "Göstəriş (modus) nə deməkdir?", "short_answer", "Məntiqi çıxarış qaydası", 2,
         "Nəticə çıxarmaq üçün istifadə olunan formal məntiqi qayda"),

        ("Məntiq", "Həmişə yalan ifadəni necə adlandırırlar?", "multiple_choice", "Ziddiyyət", 1,
         [("Tautologiya", False), ("Ziddiyyət", True), ("Kontingent", False), ("Aksioma", False)]),
    ]

    # ========== PEYK MÜHƏNDİSLİYİ (20 questions) ==========
    peyk_questions = [
        ("Peyk mühəndisliyi", "Süni peyklərin orbitə çıxarılması üçün hansı sürət lazımdır?", "multiple_choice", "Birinci kosmik sürət (7.9 km/s)", 2,
         [("Birinci kosmik sürət (7.9 km/s)", True), ("İkinci kosmik sürət (11.2 km/s)", False), ("Üçüncü kosmik sürət (16.7 km/s)", False), ("Dördüncü kosmik sürət (20 km/s)", False)]),

        ("Peyk mühəndisliyi", "GEO orbiti nədir?", "multiple_choice", "Geosinxron Ekvatorial Orbit", 2,
         [("Aşağı Yer Orbiti", False), ("Orta Yer Orbiti", False), ("Geosinxron Ekvatorial Orbit", True), ("Qütb Orbiti", False)]),

        ("Peyk mühəndisliyi", "LEO orbiti 2000 km-dən aşağı hündürlükdədir.", "true_false", "True", 1, None),

        ("Peyk mühəndisliyi", "CubeSat nədir?", "short_answer", "Kiçik standart ölçülü peyk", 2,
         "10x10x10 sm standart ölçülü kiçik tədqiqat peyyi"),

        ("Peyk mühəndisliyi", "Peyk alt sistemlərini (ADCS, EPS, TTC, Payload) izah edin və hər birinin funksiyasını göstərin.", "essay", None, 5,
         "Cavabda orientasiya, enerji təchizatı, rabitə və faydalı yük sistemləri haqqında məlumat olmalıdır"),

        ("Peyk mühəndisliyi", "Günəş panelləri peykin hansı alt sisteminə aiddir?", "multiple_choice", "EPS (Elektrik Enerji Sistemi)", 2,
         [("ADCS", False), ("EPS (Elektrik Enerji Sistemi)", True), ("TTC", False), ("Payload", False)]),

        ("Peyk mühəndisliyi", "Keplerin birinci qanununa görə, orbit ellips formalıdır.", "true_false", "True", 1, None),

        ("Peyk mühəndisliyi", "Doppler effekti peyk rabitəsində nə üçün əhəmiyyətlidir?", "short_answer", "Tezlik dəyişməsini kompensasiya etmək", 2,
         "Peyin hərəkəti nəticəsində siqnalın tezliyinin dəyişməsini düzəltmək üçün"),

        ("Peyk mühəndisliyi", "Peyk missiyasının həyat dövrünü izah edin və hər mərhələdə görülən işləri təsvir edin.", "essay", None, 5,
         "Cavabda konsept, dizayn, istehsal, sınaq, buraxılış və əməliyyat mərhələləri izah edilməlidir"),

        ("Peyk mühəndisliyi", "Azərbaycanın ilk telekommunikasiya peyyi hansıdır?", "multiple_choice", "Azerspace-1", 2,
         [("Azersky", False), ("Azerspace-1", True), ("Azerspace-2", False), ("AzerSat", False)]),

        ("Peyk mühəndisliyi", "Günəş küləyi peyklərin elektronikasına zərər verə bilər.", "true_false", "True", 1, None),

        ("Peyk mühəndisliyi", "TLE (Two-Line Element) nə üçün istifadə olunur?", "short_answer", "Peyk orbitini təsvir etmək", 2,
         "Peyin orbital parametrlərini təsvir edən standart format"),

        ("Peyk mühəndisliyi", "Peyk üçün termal nəzarət sistemlərini və onların əhəmiyyətini izah edin.", "essay", None, 5,
         "Cavabda passiv və aktiv termal nəzarət, kosmosun temperatur şəraiti haqqında məlumat olmalıdır"),

        ("Peyk mühəndisliyi", "Hansı tezlik diapazonunda peyklər rabitə qururlar?", "multiple_choice", "C, Ku, Ka bandları", 2,
         [("AM/FM radiosu", False), ("C, Ku, Ka bandları", True), ("WiFi tezlikləri", False), ("Bluetooth bandları", False)]),

        ("Peyk mühəndisliyi", "Peyk yerdən idarə edilərkən işıq sürəti gecikmələri nəzərə alınmalıdır.", "true_false", "True", 1, None),

        ("Peyk mühəndisliyi", "Reaction wheel nədir?", "short_answer", "Peyin orientasiyasını idarə edən cihaz", 2,
         "ADCS sistemində peyin bucaq mövqeyini dəyişmək üçün istifadə olunan fırlanan təkər"),

        ("Peyk mühəndisliyi", "Remote Sensing peyklərinin tətbiqlərini və sensor növlərini izah edin.", "essay", None, 5,
         "Cavabda multispektral, hiperspektral, radar görüntüləmə və tətbiq sahələri izah edilməlidir"),

        ("Peyk mühəndisliyi", "Hohmann transfer orbiti nə üçün istifadə olunur?", "multiple_choice", "Orbitlər arası enerji səmərəli keçid", 2,
         [("Peykin sürətləndirilməsi", False), ("Orbitlər arası enerji səmərəli keçid", True), ("Rabitə keyfiyyətinin artırılması", False), ("Peyin fırlanmasının idarəsi", False)]),

        ("Peyk mühəndisliyi", "Kosmik zibil (space debris) peyklər üçün təhlükə mənbəyidir.", "true_false", "True", 1, None),

        ("Peyk mühəndisliyi", "Link budget nədir?", "short_answer", "Rabitə kanalının enerji balansı", 2,
         "Ötürücüdən qəbulediciyə qədər siqnalın gücünün və itkilərinin hesablanması"),
    ]

    # ========== TELEKOMUNİKASİYA (20 questions) ==========
    telekomunikasiya_questions = [
        ("Telekomunikasiya", "OSI modelində neçə təbəqə var?", "multiple_choice", "7", 1,
         [("5", False), ("7", True), ("9", False), ("10", False)]),

        ("Telekomunikasiya", "TCP və UDP protokolları arasında əsas fərq nədir?", "multiple_choice", "TCP əlaqə yönümlüdür, UDP deyil", 2,
         [("TCP əlaqə yönümlüdür, UDP deyil", True), ("UDP daha yavaşdır", False), ("TCP şifrələməni dəstəkləmir", False), ("Fərq yoxdur", False)]),

        ("Telekomunikasiya", "Fiber optik kabel işıq siqnalları ilə məlumat ötürür.", "true_false", "True", 1, None),

        ("Telekomunikasiya", "Bandgenişliyi nə deməkdir?", "short_answer", "Verilənlərin ötürülmə sürəti", 2,
         "Vahid zamanda ötürülə bilən məlumatın həcmi"),

        ("Telekomunikasiya", "5G texnologiyasının əsas xüsusiyyətlərini və 4G-dən fərqlərini izah edin.", "essay", None, 5,
         "Cavabda sürət, gecikmə, cihaz sıxlığı və tətbiq sahələri haqqında məlumat olmalıdır"),

        ("Telekomunikasiya", "IP ünvanı nə üçün istifadə olunur?", "multiple_choice", "Şəbəkədə cihazı müəyyənləşdirmək", 2,
         [("Şəbəkədə cihazı müəyyənləşdirmək", True), ("Məlumatı şifrələmək", False), ("Virusa qarşı müdafiə", False), ("Sürəti artırmaq", False)]),

        ("Telekomunikasiya", "HTTPS protokolu HTTP-dən daha təhlükəsizdir.", "true_false", "True", 1, None),

        ("Telekomunikasiya", "MAC ünvanı nədir?", "short_answer", "Fiziki şəbəkə kartının unikal ünvanı", 2,
         "Media Access Control - şəbəkə interfeysinin donanım ünvanı"),

        ("Telekomunikasiya", "MIMO texnologiyasını və simsiz rabitədə əhəmiyyətini izah edin.", "essay", None, 5,
         "Cavabda Multiple Input Multiple Output, antenalar və məlumat ötürmə sürəti haqqında məlumat olmalıdır"),

        ("Telekomunikasiya", "DNS nə üçün istifadə olunur?", "multiple_choice", "Domen adlarını IP ünvanına çevirmək", 2,
         [("Məlumatı sıxmaq", False), ("Domen adlarını IP ünvanına çevirmək", True), ("Virusları silmək", False), ("Sürəti ölçmək", False)]),

        ("Telekomunikasiya", "Latency (gecikmə) şəbəkə performansının mühüm göstəricisidir.", "true_false", "True", 1, None),

        ("Telekomunikasiya", "QoS (Quality of Service) nədir?", "short_answer", "Xidmət keyfiyyətinin idarə edilməsi", 2,
         "Şəbəkədə müxtəlif trafik növlərinin prioritetləşdirilməsi"),

        ("Telekomunikasiya", "SDN (Software-Defined Networking) konsepsiyasını və ənənəvi şəbəkələrdən fərqlərini izah edin.", "essay", None, 5,
         "Cavabda şəbəkənin mərkəzləşdirilmiş idarəsi, proqram təminatı ilə konfiqurasiya haqqında məlumat olmalıdır"),

        ("Telekomunikasiya", "VPN nə üçün istifadə olunur?", "multiple_choice", "Təhlükəsiz virtual şəbəkə yaratmaq", 2,
         [("Sürəti artırmaq", False), ("Təhlükəsiz virtual şəbəkə yaratmaq", True), ("Yaddaşı genişləndirmək", False), ("Ekranı böyütmək", False)]),

        ("Telekomunikasiya", "Modulyasiya amplitud, tezlik və ya fazanın dəyişdirilməsidir.", "true_false", "True", 1, None),

        ("Telekomunikasiya", "CDN (Content Delivery Network) nədir?", "short_answer", "Məzmunun paylanmış şəbəkəsi", 2,
         "Məzmunu istifadəçilərə yaxın serverlər vasitəsilə çatdıran sistem"),

        ("Telekomunikasiya", "Optik şəbəkələrdə WDM (Wavelength Division Multiplexing) texnologiyasını izah edin.", "essay", None, 5,
         "Cavabda dalğa uzunluğu bölgüsü, kanal tutumu və fiber optik sistemlərdə tətbiqi izah edilməlidir"),

        ("Telekomunikasiya", "LTE nəyi ifadə edir?", "multiple_choice", "Long Term Evolution", 2,
         [("Low Tech Energy", False), ("Long Term Evolution", True), ("Local Transfer Exchange", False), ("Limited Time Encryption", False)]),

        ("Telekomunikasiya", "Duplex rabitə eyni zamanda iki istiqamətdə məlumat ötürülməsi deməkdir.", "true_false", "True", 1, None),

        ("Telekomunikasiya", "SNR (Signal-to-Noise Ratio) nədir?", "short_answer", "Siqnal-səs-küy nisbəti", 2,
         "İstifadəli siqnalın fon səs-küyünə nisbəti, rabitə keyfiyyətinin göstəricisi"),
    ]

    # Combine all questions
    all_questions = (fizika_questions + astronomiya_questions + programlasdirma_questions +
                    mentiq_questions + peyk_questions + telekomunikasiya_questions)

    print(f"Preparing to insert {len(all_questions)} questions...")

    # Insert questions
    for idx, q_data in enumerate(all_questions, 1):
        topic, question_text, question_type, correct_answer, points, extra = q_data

        # Get exam_id for this topic
        exam_id = exam_ids[topic]

        # Insert question
        cursor.execute("""
            INSERT INTO questions (exam_id, question_text, question_type, correct_answer, points, explanation, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (exam_id, question_text, question_type, correct_answer, points,
              extra if question_type in ['short_answer', 'essay'] else None, idx))

        question_id = cursor.lastrowid

        # Insert options for multiple choice questions
        if question_type == "multiple_choice" and extra:
            for option_text, is_correct in extra:
                cursor.execute("""
                    INSERT INTO question_options (question_id, option_text, is_correct)
                    VALUES (?, ?, ?)
                """, (question_id, option_text, is_correct))

        if idx % 20 == 0:
            print(f"Inserted {idx} questions...")

    conn.commit()

    # Verify insertion
    cursor.execute("""
        SELECT e.title, COUNT(q.id) as count
        FROM exams e
        LEFT JOIN questions q ON e.id = q.exam_id
        WHERE e.id IN (?, ?, ?, ?, ?, ?)
        GROUP BY e.title
    """, tuple(exam_ids.values()))
    results = cursor.fetchall()

    print("\n" + "="*60)
    print("QUESTIONS SUCCESSFULLY INSERTED!")
    print("="*60)
    for topic, count in results:
        print(f"{topic}: {count} sual")

    cursor.execute("SELECT COUNT(*) FROM questions WHERE exam_id IN (?, ?, ?, ?, ?, ?)",
                   tuple(exam_ids.values()))
    total = cursor.fetchone()[0]
    print(f"\nÜmumi: {total} sual")
    print("="*60)

    conn.close()

if __name__ == "__main__":
    create_questions()
