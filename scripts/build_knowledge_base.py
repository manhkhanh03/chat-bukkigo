import json
from pathlib import Path

# Thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

knowledge_base = {
    "metadata": {
        "title": "Nail Salon AI Rezeptionistin Knowledge Base",
        "source": "AI_letan.pdf",
        "description": "Strukturierte Wissensbasis für die AI-Rezeptionistin im Nail-Studio (Schweiz/Deutschland). 3-Ebenen-Architektur: Knowledge Layer, Decision Layer, Communication Layer.",
        "primary_language": "de-CH",
        "multilingual_support": ["de-CH", "de-DE", "vi-VN", "en-US"],
        "total_pages_covered": 41
    },
    "core_principles": [
        "Internal knowledge is not a script: AI biết nhiều nhưng chỉ nói 20-40 từ.",
        "Mục tiêu cốt lõi: Dẫn dắt về đặt lịch hẹn (Booking) để thợ kiểm tra trực tiếp tại tiệm.",
        "Phân biệt FACT với RECOMMENDATION: Chỉ nói Fact kỹ thuật, không tự chẩn đoán móng qua điện thoại.",
        "An toàn y tế (Safety Escalation): Tuyệt đối không nhận ca nấm, viêm, sưng, mủ, móng xanh (Pseudomonas); khuyên đi bác sĩ chuyên khoa.",
        "Tiếp nhận khiếu nại (Complaints): Không đổ lỗi cho khách hay thợ; thu thập 4 thông tin (ngày làm, số móng, vị trí, ảnh) và mời đến kiểm tra bảo hành.",
        "Booking Flow: Xác định Dịch vụ -> Chi nhánh -> Ngày -> Giờ -> Thợ (nếu yêu cầu). Tuyệt đối KHÔNG hỏi lại thông tin khách đã cung cấp."
    ],
    "customer_vocabulary_swiss_de": [
        {
            "term": "Shellac / Gel Lack / Gellack / UV Lack",
            "meaning": "Bezieht sich auf dieselbe Servicegruppe (langanhaltender UV-Lack auf Naturnagel)",
            "intent": "service_inquiry",
            "rule": "Keine chemischen Fachvorträge halten. Klären, ob Naturnagel oder Verlängerung gewünscht ist."
        },
        {
            "term": "Shellac ist abgegangen / Es löst sich",
            "meaning": "Lifting des Produkts vom Naturnagel",
            "intent": "complaint_or_repair",
            "rule": "Nicht sofort Ferndiagnose stellen. Fragen: Wann gemacht, wie viele Nägel, wo löst es sich? Termin zur Begutachtung anbieten."
        },
        {
            "term": "Es splittert vorne",
            "meaning": "Chipping an der Nagelspitze / Free Edge",
            "intent": "complaint_or_repair",
            "rule": "Unterscheiden zwischen Chipping und Lifting. Im Rahmen der Garantie prüfen."
        },
        {
            "term": "Mein Nagel ist abgebrochen",
            "meaning": "Nagelbruch (mechanische Einwirkung oder Statikproblem)",
            "intent": "repair_or_emergency",
            "rule": "Fragen, ob Nagelbett verletzt ist/blutet. Wenn unverletzt: Reparaturtermin anbieten."
        },
        {
            "term": "Meine Nägel sind sehr dünn",
            "meaning": "Dünne, weiche Naturnägel",
            "intent": "consultation",
            "rule": "Nicht sofort behaupten 'Sie müssen Gel machen'. Empfehlen, dass die Mitarbeiterin vor Ort prüft."
        },
        {
            "term": "Ich möchte meine eigenen Nägel behalten",
            "meaning": "Kunde möchte Naturnägel behalten (keine künstliche Verlängerung)",
            "intent": "service_selection",
            "rule": "Richtung Shellac oder Naturnagelverstärkung (Gel Verstärkung) ohne Verlängerung lenken."
        },
        {
            "term": "Ich möchte sie länger",
            "meaning": "Verlängerung erwünscht",
            "intent": "service_selection",
            "rule": "Fragen, ob natürliche Nägel wachsen gelassen werden sollen oder sofortige Nagelverlängerung (Gel/Acryl) gewünscht ist."
        },
        {
            "term": "Auffüllen / Refill",
            "meaning": "Nachbehandlung des herausgewachsenen Kunstnagels (Gel oder Acryl)",
            "intent": "booking_refill",
            "rule": "Standard-Rhythmus ca. 3–4 Wochen. Nicht den gesamten Nagel neu aufbauen, sondern auffüllen."
        },
        {
            "term": "HEMA-free",
            "meaning": "Produkt ohne HEMA-Monomer",
            "intent": "safety_inquiry",
            "rule": "Klarstellen: HEMA-free bedeutet nicht automatisch 100% allergiefrei. Bei bekannten Allergien Vorsicht."
        },
        {
            "term": "Nagel grün / Greenie",
            "meaning": "Pseudomonas-Bakterieninfektion unter dem Coating",
            "intent": "safety_emergency",
            "rule": "Nicht überlackieren! Produkt entfernen, trocknen lassen, nicht behandeln bis ausgeheilt."
        }
    ],
    "chunks": [
        # --- SHELLAC SECTION ---
        {
            "id": "shellac_definition_facts",
            "category": "service_detail",
            "service": "shellac",
            "topic": "definition",
            "query_samples": [
                "Was ist Shellac?",
                "Shellac thực chất là gì?",
                "Sơn Shellac là gì?",
                "What is Shellac?"
            ],
            "facts": "Shellac ist eine langanhaltende Farbbeschichtung für den Naturnagel, die unter UV-/LED-Licht polymerisiert wird. Es ist dünner und natürlicher als Gel/Acryl und lässt sich durch Soak-off schonend ablösen.",
            "boundary_rules": "Nicht als Nagelverlängerung anpreisen. Keine chemischen Details ungefragt vortragen.",
            "sample_dialogue": {
                "de_CH": "Shellac ist eine langanhaltende Farbbeschichtung für den Naturnagel, die unter UV-/LED-Licht gehärtet wird. Sie ist dünner und natürlicher als klassisches Gel. Möchten Sie einen Termin vereinbaren?",
                "vi_VN": "Shellac là lớp sơn màu bền đẹp trên móng tự nhiên, được làm cứng dưới đèn UV/LED. Lớp sơn mỏng và tự nhiên hơn đắp gel. Chị có muốn em kiểm tra lịch hẹn để qua tiệm làm không ạ?"
            },
            "keywords": ["shellac", "definition", "uv led", "farbbeschichtung", "naturnagel", "gel polish"]
        },
        {
            "id": "shellac_vs_regular_polish",
            "category": "service_comparison",
            "service": "shellac",
            "topic": "comparison_regular",
            "query_samples": [
                "Wie unterscheidet sich Shellac von normalem Nagellack?",
                "Shellac khác sơn thường như thế nào?",
                "Sơn thường với shellac khác gì nhau?"
            ],
            "facts": "Normaler Nagellack trocknet an der Luft und hält wenige Tage. Shellac polymerisiert unter UV/LED, hält meist 2–3 Wochen, glänzt stark und ist stoßfester, benötigt aber ein professionelles Ablösen.",
            "boundary_rules": "Keine 100%ige Haltbarkeitsgarantie von 3 Wochen versprechen.",
            "sample_dialogue": {
                "de_CH": "Normaler Lack trocknet an der Luft und hält wenige Tage. Shellac wird unter UV-/LED-Licht gehärtet, hält ca. 2–3 Wochen und hat einen dauerhaften Glanz. Soll ich Ihnen einen Termin reservieren?",
                "vi_VN": "Sơn thường tự khô ngoài không khí và giữ được vài ngày. Shellac được sấy đèn UV/LED, giữ bóng đẹp khoảng 2–3 tuần. Em kiểm tra lịch hẹn cho chị nhé?"
            },
            "keywords": ["vergleich", "normaler nagellack", "haltbarkeit", "son thuong", "do ben"]
        },
        {
            "id": "shellac_vs_gel",
            "category": "service_comparison",
            "service": "shellac",
            "topic": "comparison_gel",
            "query_samples": [
                "Was ist der Unterschied zwischen Shellac und Gel?",
                "Was ist besser, Shellac oder Gel?",
                "Shellac khác Gel như thế nào?",
                "Nên làm Shellac hay Gel?"
            ],
            "facts": "Shellac ist eine dünne Farbbeschichtung auf dem Naturnagel ohne nennenswerten Aufbau. Gel (Builder Gel) baut Struktur auf, stabilisiert weiche/lange Nägel und ermöglicht Nagelverlängerungen.",
            "boundary_rules": "Nicht pauschal sagen 'Gel ist besser' oder 'Shellac ist besser'. Kundenwunsch erfragen: Nur lackieren oder Nägel verstärken/verlängern?",
            "sample_dialogue": {
                "de_CH": "Shellac ist eine dünne Farbschicht für den Naturnagel. Gel dient dem Aufbau, verstärkt weiche Nägel und kann verlängern. Möchten Sie Ihre Naturnägel betonen oder wünschen Sie mehr Stabilität?",
                "vi_VN": "Shellac là lớp sơn mỏng phủ móng thật. Gel giúp tạo cấu trúc, gia cố móng yếu và có thể nối dài. Chị muốn giữ móng tự nhiên hay cần gia cố thêm ạ?"
            },
            "keywords": ["shellac vs gel", "aufbau", "verstaerkung", "gia co", "noi mong"]
        },
        {
            "id": "shellac_thin_weak_nails",
            "category": "service_detail",
            "service": "shellac",
            "topic": "weak_nails",
            "query_samples": [
                "Meine Nägel sind sehr dünn und brechen schnell, geht Shellac?",
                "Móng tôi rất mỏng và yếu thì có làm Shellac được không?",
                "Móng mềm dễ gãy sơn shellac được không?"
            ],
            "facts": "Bei sehr dünnen, weichen Nägeln kann Shellac allein oft nicht genug Stabilität bieten. Eine Naturnagelverstärkung mit Gel (Gel Verstärkung) kann sinnvoller sein. Begutachtung vor Ort ist zwingend erforderlich.",
            "boundary_rules": "NIEMALS per Telefon behaupten: 'Ihre Nägel sind zu dünn, Sie MÜSSEN Gel machen.' Immer auf Begutachtung durch Technikerin im Salon verweisen.",
            "sample_dialogue": {
                "de_CH": "Grundsätzlich geht Shellac auch auf Naturnägeln. Bei sehr dünnen Nägeln kann eine zusätzliche Gel-Verstärkung sinnvoll sein. Unsere Mitarbeiterin sieht sich das gerne kurz vor Ort an. Darf ich einen Termin vorschlagen?",
                "vi_VN": "Móng thật vẫn làm Shellac được ạ. Nếu móng mỏng hoặc mềm, phương án gia cố Gel có thể phù hợp hơn. Thợ bên em sẽ xem móng trực tiếp để tư vấn chuẩn nhất cho chị nhé."
            },
            "keywords": ["dünne naegel", "weiche naegel", "mong mong", "mong yeu", "verstaerkung"]
        },
        {
            "id": "shellac_extension_bite_nails",
            "category": "service_detail",
            "service": "shellac",
            "topic": "extension_and_nail_biting",
            "query_samples": [
                "Kann man mit Shellac Nägel verlängern?",
                "Móng ngắn do cắn móng có làm Shellac nối dài được không?",
                "Tôi hay cắn móng có làm móng được không?"
            ],
            "facts": "Shellac selbst verlängert die Nägel nicht. Bei abgekauten Nägeln oder Verlängerungswunsch empfiehlt sich eine Gel- oder Acrylmodellage mit Schablone/Tip. Im Salon wird der Zustand des Restnagels geprüft.",
            "boundary_rules": "Nicht versprechen, dass jeder Nagel gerettet werden kann, aber positiv aufzeigen, dass bei kurzen Nägeln Verlängerung/Aufbau möglich ist.",
            "sample_dialogue": {
                "de_CH": "Mit Shellac allein kann man nicht verlängern. Bei kurzen oder abgekauten Nägeln können wir mit Gel oder Acryl verlängern und stabilisieren. Möchten Sie vorbeikommen, damit wir die Nägel ansehen?",
                "vi_VN": "Shellac không dùng để nối dài móng ạ. Với móng ngắn hoặc cắn móng, bên em có thể nối dài và làm cứng bằng Gel hoặc Acryl. Chị muốn em đặt lịch để thợ xem trực tiếp không ạ?"
            },
            "keywords": ["verlaengerung", "abgekaute naegel", "mong can", "noi dai", "extension"]
        },
        {
            "id": "shellac_durability_and_warranty",
            "category": "service_detail",
            "service": "shellac",
            "topic": "durability",
            "query_samples": [
                "Wie lange hält Shellac?",
                "Sơn Shellac giữ được bao lâu?",
                "Có chắc chắn giữ được 3 tuần không?"
            ],
            "facts": "Shellac hält in der Regel 2 bis 3 Wochen, abhängig von Nagelbeschaffenheit, Beanspruchung (Wasser, Putzen) und Pflege. Die Salon-Garantie beträgt üblicherweise 1 Woche.",
            "boundary_rules": "NIEMALS versprechen 'Hält garantiert 3 Wochen'. Haltbarkeit (2-3 Wochen) nicht mit Garantie (1 Woche) verwechseln.",
            "sample_dialogue": {
                "de_CH": "Shellac hält meistens 2 bis 3 Wochen, je nach Naturnagel und täglicher Beanspruchung. Unser Salon gibt eine einwöchige Garantie. Wann passt es Ihnen am besten für einen Termin?",
                "vi_VN": "Shellac thường giữ được 2 đến 3 tuần tùy tình trạng móng và sinh hoạt hằng ngày. Salon có chính sách bảo hành 1 tuần. Chị tiện làm vào khung giờ nào ạ?"
            },
            "keywords": ["haltbarkeit", "garantie", "do ben", "bao hanh", "3 wochen"]
        },
        {
            "id": "shellac_removal_damage",
            "category": "service_detail",
            "service": "shellac",
            "topic": "removal",
            "query_samples": [
                "Macht Shellac die Nägel kaputt?",
                "Wie entfernt man Shellac?",
                "Sơn Shellac có làm hại móng không?",
                "Tự bóc sơn Shellac ở nhà được không?"
            ],
            "facts": "Shellac schädigt gesunde Nägel bei fachgerechter Anwendung und Entfernung nicht. Schäden entstehen meist durch Abziehen/Abknibbeln (reißt Keratinschichten mit) oder falsches Abfeilen. Entfernung erfolgt schonend per Soak-off Remover.",
            "boundary_rules": "Kunden dringend davon abraten, Shellac selbst abzureißen.",
            "sample_dialogue": {
                "de_CH": "Shellac schadet den Nägeln bei richtiger Anwendung und Entfernung nicht. Bitte niemals selbst abziehen, da dies die Nagelschichten beschädigt. Wir entfernen das professionell und schonend.",
                "vi_VN": "Shellac không hại móng nếu được tháo đúng cách. Chị không nên tự bóc vì dễ làm rách lớp sừng móng thật. Khi cần tháo, chị ghé tiệm để bên em ủ tháo chuyên dụng nhé."
            },
            "keywords": ["entfernung", "soak off", "abziehen", "schaden", "thao mong", "hai mong"]
        },
        {
            "id": "shellac_toenails",
            "category": "service_detail",
            "service": "shellac",
            "topic": "pedicure",
            "query_samples": [
                "Geht Shellac auch auf den Fußnägeln?",
                "Sơn Shellac móng chân được không?",
                "Làm Shellac chân có bền không?"
            ],
            "facts": "Shellac auf Fußnägeln ist sehr beliebt und hält oft länger als an den Händen (langsames Wachstum, weniger Hebelwirkung). Produkt sollte nicht zu dick aufgetragen werden, um Druckschmerzen in geschlossenen Schuhen zu vermeiden.",
            "boundary_rules": "Fußnägel nicht zu dick mit Gel aufbauen, da sonst Schuhe drücken.",
            "sample_dialogue": {
                "de_CH": "Ja, Shellac auf Fußnägeln ist ideal und hält oft sogar länger als an den Händen. Wir tragen es angenehm dünn auf, damit in geschlossenen Schuhen nichts drückt. Soll ich Ihnen einen Pédicure-Termin buchen?",
                "vi_VN": "Dạ được ạ, Shellac làm móng chân rất bền và đẹp tự nhiên, bên em sơn mỏng nhẹ để không bị cộm khi mang giày. Chị có muốn đặt lịch làm chân không ạ?"
            },
            "keywords": ["fussnaegel", "pedicure", "toenails", "mong chan", "pedikure"]
        },

        # --- GEL SECTION ---
        {
            "id": "gel_definition_and_systems",
            "category": "service_detail",
            "service": "gel",
            "topic": "definition",
            "query_samples": [
                "Was ist Gel?",
                "Làm móng Gel là gì?",
                "Gel có những loại nào?"
            ],
            "facts": "Gel ist ein UV/LED-reaktives Acrylatsystem zur Stabilisierung, Formgebung und Verlängerung von Nägeln. Es umfasst Base Gel, Aufbau-/Builder Gel, Sculpting Gel, Camouflage Gel und Versiegelungsgel.",
            "boundary_rules": "Gel ist nicht nur 'lange Kunstnägel', sondern kann auch auf ganz kurzen Naturnägeln angewendet werden.",
            "sample_dialogue": {
                "de_CH": "Gel ist ein modellierbares Material, das unter UV-/LED-Licht gehärtet wird. Es eignet sich sowohl zur Verstärkung kurzer Naturnägel als auch für Nagelverlängerungen. Was möchten Sie gerne machen lassen?",
                "vi_VN": "Gel là vật liệu tạo phom và làm cứng móng dưới đèn UV/LED, phù hợp cho cả móng tự nhiên lẫn nối dài móng. Chị đang muốn làm kiểu móng như thế nào ạ?"
            },
            "keywords": ["gel", "builder gel", "aufbau", "dap gel", "mong gel"]
        },
        {
            "id": "gel_verstaerkung_vs_verlaengerung",
            "category": "service_detail",
            "service": "gel",
            "topic": "reinforcement_vs_extension",
            "query_samples": [
                "Was ist eine Naturnagelverstärkung mit Gel?",
                "Gia cố móng Gel Verstärkung là gì?",
                "Gel Verstärkung khác gì Verlängerung?"
            ],
            "facts": "Gelverstärkung (Naturnagelverstärkung) stabilisiert die eigene Nagellänge mit einer Gelschicht, ohne die Nägel zu verlängern. Gelverlängerung baut den Nagel über Tip oder Schablone zusätzlich in die Länge aus.",
            "boundary_rules": "Gelverstärkung ≠ Nagelverlängerung.",
            "sample_dialogue": {
                "de_CH": "Bei einer Gel-Verstärkung bleibt Ihre eigene Nagellänge erhalten, sie wird nur stabiler gemacht. Eine Verlängerung verlängert den Nagel zusätzlich über Schablone oder Tip. Was wäre Ihnen lieber?",
                "vi_VN": "Gia cố Gel Verstärkung giúp móng thật chắc khỏe theo chiều dài hiện tại mà không nối thêm. Còn nối dài Verlängerung sẽ đắp thêm móng. Chị đang nghiêng về hướng nào ạ?"
            },
            "keywords": ["naturnagelverstaerkung", "verlaengerung", "gia co", "noi mong", "schablone", "tip"]
        },
        {
            "id": "gel_refill_auffuellen",
            "category": "service_detail",
            "service": "gel",
            "topic": "refill",
            "query_samples": [
                "Was ist Gel Auffüllen?",
                "Wie oft muss man Gel auffüllen?",
                "Bao lâu thì cần refill/auffüllen Gel?",
                "Có phải tháo hết ra mỗi lần làm lại không?"
            ],
            "facts": "Beim Auffüllen (Refill) wird die herausgewachsene Stelle am Nagelbett neu vorbereitet und mit Gel ausgeglichen, der Apex neu austariert. Intakte Modellagen müssen nicht komplett entfernt werden. Empfohlener Rhythmus: ca. 3–4 Wochen.",
            "boundary_rules": "3-4 Wochen als Richtwert nennen, nicht als starres Gesetz.",
            "sample_dialogue": {
                "de_CH": "Beim Auffüllen wird das herausgewachsene Gel nach etwa 3 bis 4 Wochen an der Nagelhaut ausgeglichen und die Statik erneuert. Ein komplettes Ablösen ist nicht jedes Mal nötig. Möchten Sie einen Refill-Termin buchen?",
                "vi_VN": "Refill là dặm phần móng mới mọc ra sau 3-4 tuần và cân bằng lại phom móng, không cần phải tháo hết toàn bộ. Chị có muốn em đặt lịch dặm móng không ạ?"
            },
            "keywords": ["auffuellen", "refill", "dam mong", "3-4 wochen", "apex"]
        },

        # --- ACRYL SECTION ---
        {
            "id": "acryl_definition_facts",
            "category": "service_detail",
            "service": "acryl",
            "topic": "definition",
            "query_samples": [
                "Was ist Acryl?",
                "Acryl khác Gel như thế nào?",
                "Acryl có cần hơ đèn không?",
                "Đắp bột Acryl là gì?"
            ],
            "facts": "Klassisches Acryl besteht aus flüssigem Monomer und Polymer-Pulver. Es härtet durch eine chemische Reaktion an der Luft ohne UV-/LED-Lampe aus (sofern nicht mit Gel-Polish versiegelt). Es ist sehr robust und belastbar.",
            "boundary_rules": "Acryl-Monomer hat einen typischen Geruch, das bedeutet aber nicht automatisch, dass es giftig ist. Nicht pauschal behaupten 'Acryl ist immer besser als Gel'.",
            "sample_dialogue": {
                "de_CH": "Acryl entsteht aus Pulver und Flüssigkeit und härtet von selbst ohne UV-Licht aus. Es ist sehr robust und widerstandsfähig. Ob Gel oder Acryl besser zu Ihnen passt, schaut sich die Technikerin gerne vor Ort an.",
                "vi_VN": "Acryl (đắp bột) kết hợp giữa dung dịch monomer và bột polymer, tự khô mà không cần đèn UV. Vật liệu này rất chắc và cứng. Thợ bên em sẽ xem tình trạng móng để tư vấn chị nên chọn Gel hay Acryl nhé."
            },
            "keywords": ["acryl", "acrylic", "pulver", "monomer", "dap bot", "ohne uv"]
        },

        # --- COMPLAINT & WARRANTY WORKFLOW ---
        {
            "id": "complaint_intake_rules",
            "category": "complaint_warranty",
            "service": "general",
            "topic": "complaint_procedure",
            "query_samples": [
                "Mein Shellac löst sich nach zwei Tagen ab!",
                "Móng mới làm hôm qua mà bị bong hết rồi!",
                "Móng bị mẻ đầu sau 2 ngày!",
                "Tôi muốn khiếu nại móng bị hỏng!"
            ],
            "facts": "Bei Reklamationen (Lifting, Chipping) NIEMALS sofort die Schuld der Kundin oder der Mitarbeiterin zuweisen. Systematisch 4 Informationen erfragen: 1. Wann gemacht? 2. Wie viele Nägel? 3. Welche Stelle (Cuticle, Spitze)? 4. Gab es Stoß/Klemmen? Foto anfragen und Vor-Ort-Termin vereinbaren.",
            "boundary_rules": "VERBOTENE SÄTZE: 'Das ist sicher Ihre Schuld' oder 'Das ist sicher der Fehler unserer Mitarbeiterin'. Keine Ferndiagnose!",
            "sample_dialogue": {
                "de_CH": "Das tut mir leid. Können Sie mir sagen, wann Sie bei uns waren und wie viele Nägel betroffen sind? Senden Sie uns gerne ein Foto. Wir schauen uns das direkt im Salon an und bessern es im Rahmen unserer Garantie aus.",
                "vi_VN": "Em rất tiếc vì móng của chị gặp vấn đề. Chị làm dịch vụ vào hôm nào và đang bị mấy ngón ạ? Nếu tiện chị gửi giúp em tấm ảnh, bên em sẽ sắp xếp lịch để kiểm tra và bảo hành cho chị nhé."
            },
            "keywords": ["reklamation", "beschwerde", "loest sich", "abgegangen", "khieu nai", "bong mong", "me mong"]
        },
        {
            "id": "warranty_terms_cases",
            "category": "complaint_warranty",
            "service": "general",
            "topic": "warranty_policy",
            "query_samples": [
                "Wie lange habe ich Garantie auf Shellac / Gel?",
                "Chính sách bảo hành móng như thế nào?",
                "Làm móng được bảo hành bao lâu?"
            ],
            "facts": "Die Garantie (meist 1 Woche auf Shellac) bedeutet ein Recht auf Überprüfung im Salon. Fallunterscheidung: Fall A (nach 1 Tag 6 Nägel gelöst -> Arbeitsfehler, kostenlose Reparatur); Fall B (Nagel an Tür eingeklemmt -> Unfall, kostenpflichtige Reparatur); Fall C (Tag 6 Spitze gechippt -> Garantieprüfung); Fall D (Tag 18 Herausgewachsen -> normaler Verschleiß).",
            "boundary_rules": "Garantie bedeutet nicht automatisch kostenlose Reparatur bei eigenem Verschulden (Gewalteinwirkung).",
            "sample_dialogue": {
                "de_CH": "Wir haben eine Garantiezeit von 7 Tagen. Innerhalb dieser Zeit prüfen wir Mängel sehr kulant bei uns im Salon. Darf ich Ihnen einen kurzen Reparaturtermin einbuchen?",
                "vi_VN": "Salon áp dụng thời gian bảo hành trong vòng 7 ngày. Khi có vấn đề bong tróc kỹ thuật, bên em sẽ kiểm tra và sửa móng cho chị tại tiệm. Em kiểm tra lịch hẹn sửa móng cho chị nhé?"
            },
            "keywords": ["garantie", "7 tage", "reparatur", "bao hanh", "sua mong"]
        },

        # --- SAFETY & ESCALATION ---
        {
            "id": "medical_safety_escalation",
            "category": "safety_escalation",
            "service": "general",
            "topic": "safety_signals",
            "query_samples": [
                "Mein Nagel ist grün unter dem Lack!",
                "Tôi bị đau, sưng và chảy mủ quanh móng",
                "Khách bị nấm móng có sơn được không?",
                "Nối mi bị sưng đỏ mắt",
                "Móng gãy chảy máu"
            ],
            "facts": "Bei Schmerzen, starker Rötung, Schwellung, Eiter, Blutung, Verdacht auf Nagelpilz oder grünen Verfärbungen (Pseudomonas) darf KEINE kosmetische Behandlung stattfinden. Die AI darf keine medizinische Diagnose stellen. Es gilt: Behandlung verweigern, Produkt schonend entfernen lassen und ärztliche Abklärung empfehlen.",
            "boundary_rules": "STRIKT VERBOTEN: 'Das ist Nagelpilz', 'Wir lackieren einfach dunkel drüber'. Sofortige Weiterleitung oder Verweis an Facharzt.",
            "sample_dialogue": {
                "de_CH": "Bei Schmerzen, Entzündungen oder Verfärbungen dürfen wir leider keine Modellage auftragen. Bitte lassen Sie das von einem Arzt abklären, damit Ihr Nagel gesund heilen kann.",
                "vi_VN": "Khi móng có dấu hiệu sưng đau, viêm hoặc đổi màu bất thường, salon xin phép không nhận làm móng để đảm bảo an toàn. Chị nên đi khám bác sĩ chuyên khoa để kiểm tra trước ạ."
            },
            "keywords": ["schmerzen", "roetung", "schwellung", "eiter", "nagelpilz", "nagel gruen", "nam mong", "sung dau", "di ung"]
        },

        # --- BOOKING FLOW & SALON POLICIES ---
        {
            "id": "booking_flow_rules",
            "category": "booking_policy",
            "service": "general",
            "topic": "flow_and_stylist",
            "query_samples": [
                "Ich möchte einen Termin buchen",
                "Tôi muốn đặt lịch làm móng",
                "Tôi muốn làm với thợ Karin thứ Sáu lúc 15h ở Oerlikon"
            ],
            "facts": "Booking Flow: 1. Service -> 2. Filiale (z.B. Oerlikon, Schaffhausen) -> 3. Tag/Uhrzeit -> 4. Wunschmitarbeiterin. REZIS-REGEL: Bereits genannte Informationen NIEMALS nochmals abfragen! Ist die Wunschmitarbeiterin belegt, nächste freie Zeit vorschlagen oder fragen, ob andere Kollegin recht ist.",
            "boundary_rules": "Keine Termine bestätigen, bevor sie im System tatsächlich eingebucht sind. Keine Preise erfinden.",
            "sample_dialogue": {
                "de_CH": "Sehr gerne! Am Freitag um 15:00 Uhr bei Karin in Oerlikon ist noch frei. Darf ich den Termin verbindlich auf Ihren Namen buchen?",
                "vi_VN": "Dạ được ạ! Thứ Sáu lúc 15:00 với chị Karin ở chi nhánh Oerlikon vẫn còn trống. Em chốt lịch hẹn này cho chị nhé?"
            },
            "keywords": ["termin buchen", "booking", "filiale", "mitarbeiterin", "dat lich", "chi nhanh", "tho lam"]
        },
        {
            "id": "booking_children_policy",
            "category": "booking_policy",
            "service": "general",
            "topic": "children",
            "query_samples": [
                "Dürfen Kinder Nägel machen lassen?",
                "Trẻ em bao nhiêu tuổi thì được làm móng?",
                "Con gái tôi 12 tuổi muốn làm móng"
            ],
            "facts": "Bei Kindern und Jugendlichen unter 15 Jahren dürfen keine aggressiven Modellagen durchgeführt werden. Normales Feilen und einfacher Lack sind mit Einverständnis der Eltern möglich. Ein Erziehungsberechtigter sollte anwesend sein oder eine schriftliche Bestätigung vorliegen.",
            "boundary_rules": "Keine Acryl-/Gelverlängerungen für Kinder versprechen.",
            "sample_dialogue": {
                "de_CH": "Für Jugendliche unter 15 Jahren bieten wir gerne schonende Maniküre und normalen Lack an, wenn die Eltern einverstanden sind. Darf ich für Sie und Ihre Tochter einen Termin anfragen?",
                "vi_VN": "Với các bé dưới 15 tuổi, bên em chỉ nhận cắt da, dũa móng và sơn thường nhẹ nhàng khi có phụ huynh đồng ý. Chị muốn đặt lịch cho bé vào hôm nào ạ?"
            },
            "keywords": ["kinder", "jugendliche", "unter 15", "tre em", "tuoi lam mong"]
        }
    ]
}

output_path = DATA_DIR / "nail_receptionist_kb.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(knowledge_base, f, ensure_ascii=False, indent=2)

print(f"Erfolgreich erstellt: {output_path}")
print(f"Anzahl Chunks: {len(knowledge_base['chunks'])}")
print(f"Anzahl Schweizerdeutsch-Vokabeln: {len(knowledge_base['customer_vocabulary_swiss_de'])}")
