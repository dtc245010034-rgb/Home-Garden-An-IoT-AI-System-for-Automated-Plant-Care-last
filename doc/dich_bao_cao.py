"""Tao ban tieng Viet cua Final Report tu ban da chen anh.

Doc lai .docx theo dung thu tu da trich trong _extract.json, doi chieu nguyen ban
truoc khi ghi de nen khong so lech chi so. Anh, bang bieu va dinh dang doan van
giu nguyen; chi noi dung chu thay doi.

    python doc/dich_bao_cao.py doc/SIC_IoT_Final_Report_CO_ANH.docx \
                               doc/_extract.json \
                               doc/SIC_IoT_Final_Report_TiengViet.docx
"""
import json
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn

SRC, EXTRACT, OUT = (Path(a) for a in sys.argv[1:4])

# Giu nguyen: dinh danh ma nguon, so do, don vi, ma muc tieu / kiem thu.
# Chi so nao khong co trong T thi giu nguyen van ban goc.
T = {
0: "Samsung Innovation Campus — Khoá học IoT",
1: "Đồ án Capstone — Báo cáo cuối kỳ",
2: "Smart Home Garden: Hệ thống IoT–AI chăm sóc cây trồng tự động",
4: "[ TÊN NHÓM ]",
5: "[ Tên nhóm trưởng ] (Nhóm trưởng)",
6: "[ Thành viên 2 ]",
7: "[ Thành viên 3 ]",
8: "[ Thành viên 4 ]",
10: "Mục lục",
11: "1.  Giới thiệu",
12: "1.1.  Bối cảnh",
13: "1.2.  Động lực và mục tiêu",
14: "1.3.  Thành viên và phân công",
15: "1.4.  Tiến độ và các mốc",
16: "2.  Triển khai đồ án",
17: "2.1.  Mô hình dịch vụ IoT",
18: "2.2.  Xử lý dữ liệu",
19: "2.3.  Hiện thực dịch vụ",
20: "2.4.  Thiết kế hệ thống",
21: "3.  Kết quả",
22: "3.1.  Thu thập dữ liệu (cảm biến, cơ cấu chấp hành, bộ điều khiển)",
23: "3.2.  Mạng và truyền thông",
24: "3.3.  Hiện thực phần cứng",
25: "3.4.  Trực quan hoá dữ liệu",
26: "3.5.  Kiểm thử và cải tiến",
27: "4.  Tác động dự kiến",
28: "4.1.  Kết quả đạt được và lợi ích",
29: "4.2.  Hướng cải tiến",
30: "5.  Nhận xét của thành viên",
31: "6.  Nhận xét của giảng viên",
32: "1. Giới thiệu",
33: "1.1. Bối cảnh",
34: "Rau ăn lá ngắn ngày — cải ngọt, cải thìa và các loại cải tương tự — là nhóm cây "
    "được hộ gia đình ở thành phố Việt Nam trồng nhiều nhất, thường trong khay đặt trên "
    "ban công hoặc sân thượng. Chu kỳ từ gieo đến thu hoạch khoảng ba mươi đến bốn mươi "
    "ngày, nghĩa là chỉ một tuần tưới không đúng cũng đủ mất cả lứa. Lo ngại về dư lượng "
    "thuốc bảo vệ thực vật trong rau ngoài chợ tiếp tục đẩy các hộ sang tự trồng, nhưng "
    "sự chăm sóc hằng ngày mà cây đòi hỏi lại đúng là thứ người đi làm không thể bảo đảm.",
35: "Tự động hoá việc tưới bản thân nó không khó, và các bộ điều khiển rẻ tiền đã giải "
    "quyết được. Một đầu dò độ ẩm đất loại điện trở hoặc điện dung được đọc và so với một "
    "ngưỡng cố định, relay đóng bơm khi giá trị xuống dưới ngưỡng đó. Lớp Internet of "
    "Things thường được đắp thêm lên trên — một cloud broker, một dashboard trên điện "
    "thoại, một thông báo — cải thiện khả năng quan sát nhưng không thay đổi bản chất của "
    "quyết định. Bộ điều khiển vẫn chỉ biết đúng một điều về khu vườn: giá thể đang ẩm "
    "đến mức nào.",
36: "Chính phép đo duy nhất đó là giới hạn mà đồ án này đặt ra để giải quyết. Độ ẩm đất "
    "là đại lượng đại diện cho lượng nước sẵn có trong giá thể, không phải cho tình trạng "
    "của cây, và hai thứ này tách nhau ra đúng trong những trường hợp làm mất cả lứa rau:",
37: "Héo rũ là dấu hiệu nhập nhằng. Một cây hết nước và một cây bắt đầu thối rễ đều biểu "
    "hiện lá rũ xuống giống hệt nhau. Hai tình trạng này đòi hỏi hai phản ứng ngược nhau — "
    "tưới ngay, hoặc ngừng tưới hẳn — mà thối rễ lại xảy ra khi độ ẩm đất đang cao, nên bộ "
    "điều khiển theo ngưỡng đọc thấy độ ẩm bình thường sẽ không thấy có gì bất thường cả.",
38: "Bệnh nấm thì đầu dò đất không nhìn thấy được. Đốm nâu trên lá lây qua nước đọng trên "
    "bề mặt lá. Một bộ điều khiển chạy chu kỳ phun sương giữa trưa nóng, khi cây đã nhiễm "
    "nấm, chính là đang đẩy nhanh quá trình lây lan, và không cảm biến nào trong một hệ "
    "thông thường báo được điều này.",
39: "Thiếu dinh dưỡng cũng vô hình như vậy. Lá già vàng đồng loạt là dấu hiệu thiếu đạm "
    "chứ không phải thiếu nước, nhưng hành động khắc phục duy nhất mà một bộ điều khiển "
    "chạy theo độ ẩm có thể làm lại là tưới thêm.",
40: "Điều mới thay đổi gần đây là phép đo còn thiếu — cây trông ra sao trên thực tế — đã "
    "trở nên rẻ. Các mô hình thị giác đa phương thức nay truy cập được qua API dịch vụ với "
    "chi phí mỗi lần suy luận đủ thấp để một máy tính nhúng gửi một tấm ảnh mỗi mười lăm "
    "phút liên tục không giới hạn, và Raspberry Pi 5 thừa năng lực chụp và mã hoá khung "
    "hình đó song song với các nhiệm vụ khác. Đồ án coi camera là cảm biến thứ hai, đầu ra "
    "là một nhãn tình trạng cây chứ không phải một con số, và đặt ra câu hỏi hẹp hơn phần "
    "lớn các nghiên cứu thị giác máy trong nông nghiệp: không phải mô hình phân loại bệnh "
    "chính xác đến đâu, mà là những quyết định điều khiển cụ thể nào trở nên khả thi khi có "
    "đồng thời một nhãn thị giác và một giá trị độ ẩm đất tại cùng một thời điểm.",
41: "1.2. Động lực và mục tiêu",
42: "Động lực của đồ án được diễn đạt rõ nhất bằng một tình huống hỏng duy nhất. Người "
    "trồng về nhà buổi tối và thấy cây héo rũ. Mọi bộ điều khiển thông thường trong tình "
    "huống này đều tưới. Nếu nguyên nhân là khô hạn thì đó là đúng. Nếu nguyên nhân là thối "
    "rễ trong đất vốn đã sũng nước thì việc tưới giết cây nhanh hơn. Phân biệt hai trường "
    "hợp đòi hỏi phải nhìn lá và nhìn đầu dò đất cùng lúc, đây là bài toán hợp nhất dữ liệu "
    "chứ không phải bài toán cảm biến, và đó là lý do hệ thống được xây quanh một tầng "
    "quyết định thay vì quanh một dashboard.",
43: "Động lực thứ hai đến từ chính môi trường vận hành của nhóm. Kết nối Internet ở khu dân "
    "cư tại Việt Nam nhìn chung tốt nhưng không bảo đảm, và một bộ điều khiển vườn ngừng "
    "tưới mỗi khi router khởi động lại thì không ai lắp. Kiến trúc vì vậy bị ràng buộc ngay "
    "từ đầu: phần thông minh có thể nằm ở phía trên, nhưng khả năng giữ cho cây sống phải "
    "nằm ngay trên thiết bị.",
44: "Những động lực đó được chuyển thành bảy mục tiêu, mỗi mục tiêu đều viết sao cho có thể "
    "kiểm chứng được chứ không phải để tranh luận:",
45: "STT", 46: "Mục tiêu",
48: "Đo nhiệt độ, độ ẩm không khí, ánh sáng môi trường và độ ẩm đất, đồng thời điều khiển "
    "tưới gốc và phun sương từ một vi điều khiển tự nó giữ một chính sách điều khiển theo "
    "ngưỡng đầy đủ.",
50: "Phân xử giữa các nguồn điều khiển cạnh tranh bằng một sơ đồ ưu tiên tất định, đánh giá "
    "lại theo chu kỳ cố định hai giây, sao cho lý do của mọi trạng thái cơ cấu chấp hành "
    "đều dựng lại được.",
52: "Thu nhận chẩn đoán tình trạng cây từ một mô hình thị giác bị ràng buộc vào một tập "
    "trạng thái cố định kèm giá trị độ tin cậy tường minh, và loại bỏ mọi phản hồi nằm "
    "ngoài tập đó hoặc dưới ngưỡng tin cậy đã công bố trước khi nó được phép tác động tới "
    "cơ cấu chấp hành.",
54: "Đối chiếu nhãn thị giác với số đo độ ẩm đất theo thời gian thực trong một ma trận hợp "
    "nhất, và chứng minh ít nhất ba ô cho ra hành động khác với một hệ chỉ dùng độ ẩm đất.",
56: "Giới hạn thời gian cho mọi lệnh ép cơ cấu chấp hành, và làm cho khoá ban đêm không thể "
    "bị ghi đè, sao cho không một lỗi phần mềm hay một người vận hành sốt ruột nào có thể "
    "để bơm chạy mãi.",
58: "Sống sót qua khởi động lại, mất điện, đứt kết nối serial và mất Internet mà không cần "
    "can thiệp thủ công, đồng thời giữ được lịch sử cảm biến sau mỗi lần khởi động lại.",
60: "Phơi bày toàn bộ trạng thái hệ thống — số đo thời gian thực, lý do quyết định, lịch sử "
    "cảm biến, kho chẩn đoán và nhật ký sự kiện — cho mọi trình duyệt trong mạng nội bộ.",
61: "Phạm vi và những gì không làm",
62: "Bản mẫu bao phủ một khay trồng được quan sát bởi một camera. Bón phân tự động nằm "
    "ngoài phạm vi; thiếu đạm chỉ được báo dưới dạng khuyến cáo. Giao diện REST không có "
    "xác thực và hệ thống dự kiến chạy trong mạng gia đình tin cậy. Các giới hạn này là chủ "
    "ý và được nói lại ở mục 4.2.",
63: "1.3. Thành viên và phân công",
64: "Công việc được chia theo tầng hệ thống để mỗi thành viên sở hữu cả một giao diện lẫn "
    "một phần hiện thực, và để không có hai thành viên nào cùng bị chặn trên một file.",
65: "Thành viên", 66: "Vai trò", 67: "Trách nhiệm và sản phẩm bàn giao",
68: "[ Tên nhóm trưởng ]",
69: "Nhóm trưởng — Phần mềm tầng biên và AI",
70: "Module chụp ảnh; thiết kế prompt Gemini Vision và kiểm chứng phản hồi; tích hợp serial, "
    "Time Guard và thị giác vào tiến trình giám sát; bộ máy quyết định năm mức và ma trận "
    "hợp nhất; triển khai (unit systemd, udev rule, lưu trữ SQLite).",
71: "[ Thành viên 2 ]",
72: "Phần cứng nhúng và firmware",
73: "Firmware ESP32: driver cảm biến và hiệu chuẩn, điều khiển relay khoá liên động, màn "
    "hình OLED, cổng cấu hình WiFiManager và trang web trên thiết bị; đi dây, cấp nguồn và "
    "vỏ hộp.",
74: "[ Thành viên 3 ]",
75: "Truyền thông và kiểm thử",
76: "Giao thức JSON serial hai chiều có tự kết nối lại; logic khoá ban đêm Time Guard; các "
    "kịch bản kiểm thử đầu cuối và video minh hoạ.",
77: "[ Thành viên 4 ]",
78: "Giao diện và tài liệu",
79: "Kiểm chứng các endpoint REST và dashboard trên trình duyệt (đồng hồ đo, nhãn trạng "
    "thái, biểu đồ sparkline, dải ảnh); Action Plan, Work Breakdown Structure, báo cáo cuối "
    "kỳ và slide thuyết trình.",
80: "1.4. Tiến độ và các mốc",
81: "Đồ án chạy từ 06/07/2026 đến 05/08/2026 trong năm giai đoạn. Giai đoạn 1 đến 4 theo "
    "đúng Work Breakdown Structure đã thống nhất từ đầu. Giai đoạn 5 được thêm vào sau khi "
    "một đợt rà soát nội bộ cuối giai đoạn 4 phát hiện ba khiếm khuyết đủ nghiêm trọng để "
    "chặn việc triển khai thực địa; giai đoạn đó và lý do của nó được mô tả ở mục 3.5.",
82: "GĐ", 83: "Thời gian", 84: "Nội dung", 85: "Phụ trách", 86: "Trạng thái",
89: "Phần cứng và firmware ESP32: tích hợp cảm biến, điều khiển relay, màn hình OLED, "
    "WiFiManager",
90: "[ Thành viên 2 ]", 91: "Xong",
94: "Truyền thông serial và khoá ban đêm Time Guard",
95: "[ Thành viên 3 ]", 96: "Xong",
99: "Tích hợp thị giác AI: module chụp ảnh, thiết kế prompt Gemini, đánh giá độ chính xác",
100: "[ Tên nhóm trưởng ]", 101: "Đang đánh giá độ chính xác",
104: "Tích hợp và triển khai hệ thống: tiến trình giám sát, service systemd, kiểm thử đầu "
     "cuối, tài liệu",
105: "[ Tên nhóm trưởng ]", 106: "Xong; đang hoàn thiện tài liệu",
109: "Củng cố độ tin cậy và hợp nhất cảm biến: phát hiện điểm mù, kiểm chứng độ tin cậy, an "
     "toàn xung có thời hạn, lưu trữ SQLite, ma trận hợp nhất, cổng serial cố định, chạy "
     "thực địa",
110: "[ Tên nhóm trưởng ]", 111: "Đang chạy thực địa và quay video demo",
112: "Các mốc",
113: "M1 — 10/07: firmware đọc đủ bốn kênh cảm biến và điều khiển cả hai relay dưới chế độ "
     "AUTO cục bộ, độc lập với mọi máy chủ.",
114: "M2 — 13/07: liên kết serial hai chiều ổn định; khoá ban đêm được kiểm chứng là chặn "
     "được việc tưới trong khung 19:00 đến 06:00.",
115: "M3 — 17/07: mô hình thị giác trả về một chẩn đoán có cấu trúc hợp lệ cho ảnh lá đã chụp.",
116: "M4 — 21/07: cả ba nguồn đầu vào được gộp vào một tiến trình giám sát chạy cây quyết "
     "định năm mức.",
117: "M5 — 25/07: service tự khởi động cùng máy và tự chạy lại sau khi lỗi.",
118: "M6 — 05/08: ma trận hợp nhất, an toàn xung có thời hạn và lưu trữ SQLite đã hoàn tất; "
     "đang chạy thực địa liên tục.",
119: "Hình 1.1 — Tiến độ đồ án (dạng Gantt của Work Breakdown Structure).",
120: "2. Triển khai đồ án",
121: "2.1. Mô hình dịch vụ IoT",
122: "Dịch vụ được mô hình hoá thành một vòng lặp liên tục cảm nhận – phân xử – tác động "
     "trên một khay trồng, trong đó người trồng đóng vai người quan sát, có thể can thiệp "
     "nhưng không bắt buộc phải có mặt để vòng lặp khép kín.",
123: "Tác nhân", 124: "Tương tác với hệ thống",
125: "Cây (khay)",
126: "Được quan sát qua bốn kênh cảm biến vật lý và một camera; được tác động qua tưới gốc "
     "và phun sương lên lá.",
127: "Hệ thống",
128: "Đọc telemetry mỗi hai giây, lấy chẩn đoán thị giác mỗi mười lăm phút, phân xử giữa hai "
     "nguồn rồi phát lệnh; ghi lại mọi số đo, chẩn đoán, lệnh và sự kiện.",
129: "Người trồng",
130: "Xem trạng thái thời gian thực, lịch sử và kho chẩn đoán từ trình duyệt trong mạng nội "
     "bộ; có thể phát lệnh thủ công có thời hạn; được cảnh báo khi camera không còn nhìn "
     "thấy cây.",
131: "Kiến trúc ba tầng",
132: "Hệ thống chia thành tầng thiết bị, tầng biên và tầng đám mây. Cách chia này ưu tiên "
     "tầng biên một cách có chủ ý: tầng đám mây đóng góp phán đoán chứ không cầm quyền điều "
     "khiển, còn tầng thiết bị giữ một chính sách dự phòng đầy đủ.",
133: "Tầng", 134: "Thành phần", 135: "Trách nhiệm",
136: "Thiết bị",
138: "Lấy mẫu bốn kênh cảm biến; điều khiển hai relay active LOW; chạy một chính sách điều "
     "khiển theo ngưỡng khép kín; phát một khung telemetry JSON mỗi hai giây; hiển thị "
     "trạng thái cục bộ trên OLED; nhận cấu hình mạng qua captive portal.",
139: "Biên",
140: "Tiến trình giám sát trên Raspberry Pi 5",
141: "Phân tích telemetry; chụp và gửi ảnh lá; kiểm chứng phản hồi của mô hình; chạy cây "
     "quyết định năm mức mỗi hai giây; lưu toàn bộ dữ liệu; phục vụ REST API và dashboard "
     "trong mạng nội bộ.",
142: "Đám mây",
144: "Trả về một chẩn đoán tình trạng cây có cấu trúc cho một ảnh được gửi lên. Không giữ "
     "trạng thái và không phát lệnh nào.",
145: "Hình 2.1 — Tổng quan kiến trúc hệ thống.",
146: "Vì sao ưu tiên tầng biên thay vì tầng đám mây",
147: "Một thiết kế thông thường sẽ đẩy telemetry lên cloud broker, đánh giá luật ở đó rồi "
     "trả lệnh về. Phương án đó bị loại vì bốn lý do.",
148: "Tiêu chí", 149: "Ưu tiên đám mây", 150: "Ưu tiên tầng biên (đã chọn)",
151: "Độ trễ điều khiển",
152: "Bị chặn bởi thời gian khứ hồi và hàng đợi của broker; không ổn định",
153: "Vòng lặp cục bộ cố định hai giây; không có mạng trong đường điều khiển",
154: "Hành vi khi mất kết nối",
155: "Việc tưới dừng cho tới khi có mạng trở lại",
156: "Tiến trình giám sát rơi về AUTO cục bộ; ESP32 vẫn chạy theo ngưỡng của chính nó ngay "
     "cả khi mất luôn tiến trình giám sát",
157: "Chi phí định kỳ",
158: "Tính tiền theo cả số thông điệp lẫn số lần suy luận",
159: "Chỉ tính theo số lần suy luận — bốn ảnh mỗi giờ",
160: "Riêng tư hình ảnh",
161: "Mọi khung hình chụp được đều rời khỏi mạng gia đình",
162: "Mỗi mười lăm phút mới có một khung hình rời mạng; telemetry thì không bao giờ",
163: "Hành vi khi hỏng từng phần",
164: "Vì mỗi tầng đều giữ chính sách riêng, hệ thống suy giảm theo từng bậc chứ không dừng "
     "hẳn. Bảng dưới đây được dùng làm hợp đồng thiết kế và từng dòng đều đã được kiểm "
     "chứng trong quá trình kiểm thử.",
165: "Sự cố", 166: "Ảnh hưởng tức thời", 167: "Phản ứng của hệ thống",
168: "Mất Internet hoặc không gọi được Gemini API",
169: "Không sinh ra chẩn đoán mới",
170: "Chẩn đoán cuối hết hiệu lực và bộ điều khiển rơi về AUTO mức 5; lỗi được ghi lại. Tình "
     "huống này đã xảy ra thật trong quá trình phát triển và được ghi nhận dưới dạng lỗi "
     "phân giải tên miền.",
171: "Tiến trình giám sát bị crash",
172: "Không còn phân xử, không thị giác, không dashboard",
173: "systemd chạy lại unit sau mười giây. Mọi cơ cấu chấp hành mà tiến trình giám sát đang "
     "ép sẽ được watchdog serial nhả trong vòng 60 giây, sau đó ESP32 tiếp tục tưới theo "
     "ngưỡng cục bộ.",
174: "Raspberry Pi mất điện",
175: "Tầng biên biến mất hoàn toàn",
176: "AUTO cục bộ của ESP32 vẫn giữ cho khay được tưới; telemetry không được lưu ở đâu nhưng "
     "quyền điều khiển vẫn còn.",
177: "Đứt cáp serial",
178: "Tiến trình giám sát mất telemetry",
179: "Luồng đọc kết nối lại theo đường thiết bị cố định. Nếu tiến trình giám sát đang ép một "
     "cơ cấu chấp hành thì watchdog serial trên thiết bị huỷ trạng thái đó sau 60 giây và "
     "quay về AUTO cục bộ; nếu vốn đã ở AUTO thì quyền điều khiển chưa từng rời thiết bị.",
180: "Rút camera hoặc camera chĩa sai",
181: "Chụp thất bại, hoặc khung hình không có cây",
182: "Số lần thất bại liên tiếp được đếm, một sự kiện cảnh báo camera được ghi và một băng "
     "cảnh báo hiện trên dashboard; chẩn đoán không được tin.",
183: "Mất điện lưới",
184: "Cả hai tầng đều dừng",
185: "Khi có điện lại, systemd khởi động service, sáu mươi phút lịch sử gần nhất được nạp "
     "lại từ cơ sở dữ liệu, và ESP32 kết nối lại bằng thông tin đã lưu.",
186: "2.2. Xử lý dữ liệu",
187: "Năm luồng dữ liệu được sinh ra ở các nhịp khác nhau và được tiến trình giám sát dung "
     "hoà thành một đối tượng trạng thái thời gian thực cùng một lịch sử cuộn.",
188: "Luồng", 189: "Nguồn", 190: "Nhịp", 191: "Lưu giữ",
192: "Khung telemetry", 193: "ESP32 qua UART", 194: "mỗi 2 giây",
195: "giá trị mới nhất giữ trong bộ nhớ, có khoá bảo vệ",
196: "Mẫu lịch sử", 197: "tiến trình giám sát", 198: "mỗi 15 giây",
199: "deque cuộn 240 mẫu — cửa sổ 60 phút",
200: "Bản ghi cơ sở dữ liệu", 201: "tiến trình giám sát", 202: "mỗi 60 giây",
203: "lưu bền vững, SQLite chế độ WAL",
204: "Ảnh lá", 205: "Camera USB qua OpenCV", 206: "mỗi 15 phút",
207: "JPEG có dấu thời gian, kho cuộn 50 file",
208: "Bản ghi chẩn đoán", 209: "Gemini Vision", 210: "mỗi 15 phút", 211: "lưu bền vững",
212: "Đường đi của telemetry",
213: "Firmware đóng gói bốn số đo cùng trạng thái hiện tại của cơ cấu chấp hành, chế độ đang "
     "hoạt động và một chuỗi lý do ngắn thành một đối tượng JSON duy nhất, rồi ghi ra cổng "
     "serial ở tốc độ 115200 baud mỗi hai giây. Luồng đọc của tiến trình giám sát phân tích "
     "từng dòng, loại bỏ riêng lẻ những khung hỏng thay vì dừng hẳn, tách khung telemetry "
     "khỏi khung sự kiện của thiết bị để một thông báo watchdog không bị hiểu nhầm thành số "
     "đo, rồi cập nhật đối tượng trạng thái dùng chung dưới khoá. Hai chuỗi dẫn xuất được "
     "duy trì từ cùng nguồn này: một cửa sổ trong bộ nhớ dùng cho biểu đồ trên dashboard, "
     "và một chuỗi bền vững nhịp thấp hơn ghi xuống cơ sở dữ liệu.",
214: "Hai bước xử lý tín hiệu được đặt trên thiết bị thay vì trên tiến trình giám sát, vì "
     "chúng thuộc về cảm biến chứ không thuộc về quyết định. Kênh ánh sáng được lấy trung "
     "bình trên hai mươi mẫu liên tiếp rồi làm mịn theo hàm mũ, trọng số 0.7 cho giá trị cũ "
     "và 0.3 cho trung bình mới, nhờ đó khử được nhiễu do bóng râm lướt qua. Kênh độ ẩm đất "
     "được quy đổi từ giá trị analog thô sang phần trăm trước khi truyền đi, để ngưỡng "
     "trong firmware và ngưỡng trong ma trận hợp nhất cùng chỉ một đại lượng.",
215: "Đường đi của thị giác và việc kiểm chứng phản hồi",
216: "Mỗi mười lăm phút, một khung hình được chụp bằng OpenCV, mã hoá JPEG, lưu vào kho với "
     "tên file có dấu thời gian và gửi tới mô hình thị giác kèm một prompt ràng buộc phản "
     "hồi phải là một đối tượng JSON gồm một trạng thái lấy từ tập cố định, một số nguyên "
     "độ tin cậy từ 0 đến 100, và một ghi chú ngắn. Prompt còn buộc mô hình phải nói rõ "
     "khung hình có chứa cây hay không.",
217: "Phản hồi của mô hình không được tin ngay khi nhận. Nó đi qua một hàm chuẩn hoá áp ba "
     "phép kiểm tra theo thứ tự, phản hồi trượt bất kỳ phép nào cũng bị hạ xuống mức không "
     "xác định và không thể chạm tới cơ cấu chấp hành:",
218: "Phản hồi phải phân tích được thành JSON với đủ ba trường mong đợi.",
219: "Trạng thái phải là một trong bốn giá trị được phép — bình thường, héo rũ, vàng lá, đốm "
     "nâu. Mọi giá trị khác, kể cả chuỗi “không xác định” do chính mô hình trả về, đều bị hạ "
     "xuống mức không xác định chứ không bị ép thành một chẩn đoán.",
220: "Độ tin cậy phải đạt ít nhất 40. Dưới ngưỡng đó, phản hồi được coi là không mang thông "
     "tin, nhờ vậy một suy luận thiếu chắc chắn không làm dịch chuyển cơ cấu chấp hành.",
221: "Việc kiểm tra khung hình có cây được xử lý ở lớp ngoài hơn: prompt buộc mô hình tự khai "
     "báo, và một bộ theo dõi sức khoẻ riêng đếm số kết quả không đáng tin liên tiếp, phát "
     "cảnh báo camera sau lần thứ ba.",
222: "Lý do đặt lớp này giữa mô hình và bộ điều khiển là vì dạng hỏng của một mô hình thị "
     "giác không phải là im lặng mà là nói sai một cách tự tin. Ở một bản trước, hệ thống "
     "chấp nhận kết luận bình thường kèm độ tin cậy bằng không rồi tiếp tục như thể cây đã "
     "được kiểm tra; lớp kiểm chứng tồn tại chính là để chặn đường đó.",
223: "Lưu trữ",
224: "Toàn bộ dữ liệu đã xử lý được ghi vào một cơ sở dữ liệu SQLite duy nhất ở chế độ "
     "write-ahead logging, trải trên bốn bảng — số đo cảm biến, chẩn đoán, lệnh đã phát và "
     "sự kiện hệ thống. Chọn chế độ WAL vì tiến trình Flask đọc cơ sở dữ liệu trong khi vòng "
     "lặp quyết định đang ghi; chế độ này cho phép đọc song song mà không chặn ghi, và giữ "
     "cho cơ sở dữ liệu vẫn phục hồi được sau khi mất điện đột ngột. Khi khởi động, tiến "
     "trình giám sát nạp lại một giờ số đo gần nhất để việc khởi động lại không tạo ra biểu "
     "đồ trống.",
225: "Hình 2.2 — Luồng xử lý dữ liệu từ cảm biến vật lý tới dashboard.",
226: "2.3. Hiện thực dịch vụ",
227: "Tầng quyết định là phần làm hệ thống này khác một bộ điều khiển theo ngưỡng, và được "
     "mô tả đầy đủ ở đây.",
228: "Cây ưu tiên năm mức",
229: "Tiến trình giám sát đánh giá lại thang dưới đây mỗi hai giây. Việc đánh giá dừng ở mức "
     "đầu tiên có điều kiện đúng, và không mức thấp nào ghi đè được mức cao hơn. Quyền thủ "
     "công duy nhất mà người vận hành nắm nằm ở mức ba, cố ý đặt dưới khoá ban đêm.",
230: "Mức", 231: "Tên", 232: "Điều kiện", 233: "Hành động",
235: "AI khẩn cấp",
236: "Chẩn đoán là héo rũ với độ tin cậy từ 70 trở lên",
237: "Vào ma trận hợp nhất; nếu đất khô thì phát một xung tưới có thời hạn 60 giây và bắt "
     "đầu cooldown một giờ",
239: "Time Guard",
240: "Giờ địa phương trong khoảng 19:00 đến 06:00",
241: "Khoá cơ cấu chấp hành ở trạng thái nghỉ. Lệnh thủ công không ghi đè được mức này.",
243: "Ghi đè thủ công",
244: "Quyền thủ công do người vận hành phát từ dashboard hoặc terminal vẫn còn hiệu lực",
245: "Giữ nguyên trạng thái đã ra lệnh cho tới hết thời hạn 600 giây, rồi nhả về AUTO",
247: "Ma trận hợp nhất",
248: "Tồn tại một chẩn đoán đã kiểm chứng và không thuộc diện khẩn cấp",
249: "Áp bảng ở phần sau — cấm phun sương, giữ nguyên việc tưới, hoặc chỉ khuyến cáo",
251: "Mặc định",
252: "Không mức nào ở trên đúng",
253: "Phát AUTO và giao quyết định cho chính các ngưỡng của ESP32",
254: "Đặt khoá ban đêm lên trên ghi đè thủ công là một quyết định thiết kế chứ không phải sơ "
     "suất. Tưới sau khi trời tối để lại nước đọng trên lá suốt đêm, đúng điều kiện mà nấm "
     "cần, và người có khả năng tưới lúc 22:00 nhất lại chính là chủ vườn vừa nhìn thấy lá "
     "rũ xuống. Vì vậy khoá này không mang tính khuyến nghị.",
255: "Hình 2.3 — Cây quyết định năm mức ưu tiên, đánh giá lại mỗi hai giây.",
256: "Ma trận hợp nhất AI × độ ẩm đất",
257: "Ma trận là cơ chế biến một nhãn thị giác thành một hành động, và là nơi cùng một triệu "
     "chứng cho ra hành vi ngược nhau tuỳ theo số đo độ ẩm đất. Cột cuối nói thẳng ô đó có "
     "làm thay đổi hành vi của cơ cấu chấp hành hay chỉ sinh ra một thông báo khuyến cáo.",
258: "Chẩn đoán", 259: "Đất khô (dưới 40 %)", 260: "Đất đủ ẩm (từ 40 % trở lên)",
261: "Có đổi hành vi cơ cấu chấp hành?",
262: "Héo rũ, độ tin cậy ≥ 70",
263: "Xung tưới có thời hạn 60 giây, sau đó nhả về AUTO",
264: "Khoá nghỉ 15 phút — nghi thối rễ, không tưới",
265: "Có",
266: "Đốm nâu",
267: "Cấm phun sương; tưới gốc vẫn chạy theo ngưỡng",
268: "Cấm phun sương; theo dõi diễn biến",
269: "Có",
270: "Vàng lá",
271: "AUTO theo ngưỡng",
272: "Ghi nhận khuyến cáo thiếu đạm; không tưới thêm",
273: "Không — chỉ khuyến cáo",
274: "Bình thường", 275: "AUTO", 276: "AUTO", 277: "Không",
278: "Không xác định",
279: "AUTO — bỏ qua chẩn đoán",
280: "AUTO — bỏ qua chẩn đoán",
281: "Không",
282: "So sánh với một hệ chỉ dùng độ ẩm đất. Ba ô ở trên là không thể đạt tới nếu không có "
     "thị giác. Ở dòng đầu, một bộ điều khiển chỉ có đầu dò đất đọc thấy độ ẩm đủ, kết luận "
     "không có gì sai và không làm gì trong khi cây chết vì thối rễ; còn ở trường hợp đất "
     "khô thì nó sẽ tưới theo lịch do đầu dò quyết định chứ không tưới ngay khi triệu chứng "
     "xuất hiện. Ở dòng thứ hai, đầu dò đất không mang bất kỳ thông tin nào về bệnh nấm, nên "
     "chu kỳ phun sương vẫn chạy bình thường và tiếp tục phát tán bào tử. Hai dòng còn lại "
     "được ghi thẳng là khuyến cáo: chẩn đoán vàng lá được ghi nhận và báo cho người trồng "
     "nhưng không làm dịch chuyển cơ cấu chấp hành, vì hành động khắc phục là bón phân mà hệ "
     "thống không có bơm định lượng.",
283: "Các cơ chế an toàn",
284: "Xung có thời hạn. Mọi lệnh ép cơ cấu chấp hành đều mang một thời điểm hết hạn. Xung "
     "tưới khẩn cấp kéo dài 60 giây, khoá thối rễ kéo dài 900 giây và quyền thủ công kéo dài "
     "600 giây; hết khoảng thời gian đó bộ điều khiển tự quay về AUTO. Không có đường thực "
     "thi nào để lại một cơ cấu chấp hành bị ép vô thời hạn.",
285: "Cooldown sau khẩn cấp. Sau một xung tưới khẩn cấp, xung tiếp theo bị chặn trong một "
     "giờ. Điều này ngăn việc một cây phục hồi chậm về mặt hình ảnh bị tưới đi tưới lại chỉ "
     "vì cùng một triệu chứng.",
286: "Lọc lệnh trùng. Một lệnh trùng với lệnh đang có hiệu lực sẽ không được phát lại, nhờ "
     "vậy liên kết serial giữ được yên tĩnh và bảng lệnh trong cơ sở dữ liệu trở thành bản "
     "ghi các lần đổi trạng thái thật chứ không phải các vòng lặp.",
287: "Ngưỡng tin cậy. Chẩn đoán dưới 40 điểm tin cậy bị loại trước khi phân xử, nên cây "
     "quyết định không bao giờ nhìn thấy nó.",
288: "Khoá liên động trên thiết bị. Relay tưới gốc và relay phun sương bị khoá liên động "
     "ngay trong firmware, nên một lỗi của tiến trình giám sát không thể đóng cả hai.",
289: "Watchdog serial. Firmware ghi lại thời điểm nhận dòng cuối cùng từ tiến trình giám "
     "sát. Nếu quá 60 giây không có lưu lượng nào trong khi trạng thái thủ công hiện tại do "
     "tiến trình giám sát áp đặt, thiết bị huỷ trạng thái đó, nhả cả hai relay, quay về AUTO "
     "cục bộ và báo sự kiện. Trạng thái thủ công đặt từ trang web của chính thiết bị thì "
     "được miễn trừ. Vì lệnh trùng bị lọc, một quyết định giữ nguyên trong nhiều phút không "
     "tự sinh ra lưu lượng serial nào, nên tiến trình giám sát gửi một PING mỗi 10 giây để "
     "phân biệt một quyết định ổn định với một máy chủ đã chết.",
290: "Các hằng số",
291: "Các hằng số tinh chỉnh được gom về một chỗ trong mã nguồn để có thể chỉnh lại chính "
     "sách cho một loại cây khác mà không phải động vào luồng điều khiển.",
292: "Hằng số", 293: "Giá trị", 294: "Ý nghĩa",
296: "2 giây", 297: "Chu kỳ đánh giá lại cây ưu tiên",
299: "40", 300: "Ngưỡng tin cậy, dưới mức này chẩn đoán bị loại",
302: "70", 303: "Độ tin cậy cần có để kích hoạt xử lý khẩn cấp mức 1",
305: "60 giây", 306: "Độ dài xung tưới khẩn cấp",
308: "3600 giây", 309: "Cửa sổ chặn sau một xung khẩn cấp",
311: "900 giây", 312: "Độ dài khoá nghỉ khi thấy héo rũ mà đất còn ẩm",
314: "600 giây", 315: "Thời hạn cấp cho một lệnh của người vận hành",
317: "60 giây", 318: "Khoảng cách tối thiểu giữa hai lần chẩn đoán do người dùng yêu cầu",
320: "40 %", 321: "Ranh giới giữa cột đất khô và cột đất đủ ẩm của ma trận hợp nhất",
323: "10 giây", 324: "Chu kỳ nhịp tim nuôi watchdog serial phía thiết bị",
326: "60 giây", 327: "Khoảng im lặng sau đó thiết bị huỷ trạng thái thủ công do tiến trình "
     "giám sát áp đặt",
329: "3", 330: "Số chẩn đoán không đáng tin liên tiếp trước khi phát cảnh báo camera",
332: "1800 giây", 333: "Cửa sổ chặn sau khi khoá thối rễ hết hạn",
334: "Mô hình đa luồng",
335: "Tiến trình giám sát chạy bốn luồng công nhân bên cạnh vòng lặp quyết định vốn chiếm "
     "luồng chính. Luồng đọc sở hữu cổng serial; luồng thị giác sở hữu camera và lời gọi "
     "mạng, cả hai đều chặn hàng giây và không được phép làm nghẽn việc phân xử; luồng "
     "dashboard chạy ứng dụng Flask; và một luồng lắng nghe bàn phím nhận lệnh gõ tại "
     "terminal trong quá trình phát triển. Trạng thái dùng chung được gói gọn trong một số "
     "ít đối tượng có khoá bảo vệ — khung telemetry mới nhất, chẩn đoán đã kiểm chứng mới "
     "nhất, và quyền thủ công đang còn hiệu lực — và mọi lệnh tới cơ cấu chấp hành đều rời "
     "tiến trình qua đúng một hàm, nhờ đó bản ghi lệnh trong cơ sở dữ liệu đầy đủ theo cấu "
     "trúc chứ không nhờ kỷ luật lập trình.",
336: "Các giao diện",
337: "Ứng dụng Flask phơi ra mười hai endpoint REST gắn trên mọi giao diện mạng ở cổng 5000 "
     "và được tiêu thụ bởi một dashboard trang đơn, trang này hỏi trạng thái thời gian thực "
     "mỗi ba giây, lịch sử mỗi hai mươi giây, dòng sự kiện mỗi ba mươi giây và số liệu tổng "
     "hợp mỗi sáu mươi giây. Các endpoint chính phục vụ trạng thái thời gian thực kèm lý do "
     "của thiết lập cơ cấu chấp hành hiện tại, lịch sử cảm biến dùng để vẽ biểu đồ, kho chẩn "
     "đoán và ảnh, nhật ký sự kiện kèm xuất CSV, và một endpoint lệnh để mở quyền thủ công.",
338: "2.4. Thiết kế hệ thống",
339: "Phần cứng",
340: "Thành phần", 341: "Kết nối", 342: "Chức năng",
344: "—",
345: "Lấy mẫu cảm biến, điều khiển relay, chính sách AUTO cục bộ, OLED, cổng cấu hình",
348: "Nhiệt độ không khí và độ ẩm tương đối",
349: "Quang trở (LDR)", 350: "GPIO34 (ADC)",
351: "Ánh sáng môi trường, lấy trung bình 20 mẫu rồi làm mịn",
352: "Đầu dò độ ẩm đất loại điện trở", 353: "GPIO35 (ADC)",
354: "Độ ẩm giá thể, quy đổi sang phần trăm ngay trên thiết bị",
355: "Relay — bơm tưới gốc", 356: "GPIO26",
357: "Active LOW; khoá liên động với relay phun sương",
358: "Relay — vòi phun sương", 359: "GPIO27",
360: "Active LOW; có thể bị ma trận hợp nhất cấm hoạt động",
361: "OLED SSD1306, 128×64", 362: "GPIO21 SDA / GPIO22 SCL",
363: "Hai trang trạng thái luân phiên mỗi ba giây",
364: "Nút BOOT", 365: "GPIO0",
366: "Giữ ba giây sẽ xoá thông tin mạng đã lưu",
368: "Serial USB, camera USB",
369: "Tiến trình giám sát, cơ sở dữ liệu, REST API và dashboard",
370: "Camera USB", 372: "Một khung ảnh lá mỗi mười lăm phút",
373: "Ngưỡng điều khiển cục bộ trong firmware",
374: "Các giá trị này định nghĩa chính sách dự phòng mức 5 và luôn có hiệu lực mỗi khi vắng "
     "tiến trình giám sát.",
375: "Ngưỡng", 376: "Giá trị", 377: "Tác dụng",
378: "Ngưỡng đất khô", 379: "40 %", 380: "Dưới mức này relay tưới được đóng",
381: "Ngưỡng nhiệt độ cao", 382: "33.0 °C",
383: "Khi khay đồng thời đang khô, hệ chọn phun sương thay vì tưới gốc",
384: "Ngưỡng tối", 385: "20 % ánh sáng",
386: "Dùng để phân biệt ngày và đêm ở mức cục bộ",
387: "Dải cảnh báo nhiệt độ", 388: "10.0 – 38.0 °C",
389: "Ra ngoài dải này, cảnh báo được phát trên OLED và trong telemetry",
390: "Phần mềm",
391: "Thành phần", 392: "Quy mô", 393: "Nội dung",
394: "Firmware ESP32 (Arduino C++)", 395: "433 dòng",
396: "Driver cảm biến, khoá liên động relay, vẽ OLED, cổng WiFiManager, trang web trên thiết "
     "bị, chính sách AUTO cục bộ, telemetry JSON và bộ phân tích lệnh",
397: "Tiến trình giám sát (Python)", 398: "1098 dòng",
399: "Luồng đọc serial, luồng thị giác, vòng lặp quyết định, ứng dụng Flask, luồng lắng nghe "
     "terminal, tầng SQLite",
400: "Dashboard (HTML/JS)", 401: "một trang đơn",
402: "Đồng hồ đo, nhãn trạng thái, hiển thị lý do quyết định, bốn biểu đồ sparkline vẽ bằng "
     "đường dẫn SVG, dải ảnh",
403: "Triển khai",
404: "Tiến trình giám sát chạy dưới dạng unit systemd với Restart=always và độ trễ khởi động "
     "lại mười giây, nhờ vậy nó chạy khi máy khởi động và tự phục hồi sau một ngoại lệ chưa "
     "bắt mà không cần can thiệp.",
405: "Một udev rule gắn board vào một đường thiết bị cố định bất kể thứ tự nhận diện, khớp "
     "cả cầu USB-serial CP2102 lẫn CH340. Việc này loại bỏ một lớp lỗi lặp đi lặp lại, trong "
     "đó tên cổng đổi qua lại giữa hai giá trị sau mỗi lần khởi động.",
406: "File cơ sở dữ liệu được mở ở chế độ write-ahead logging; ảnh được ghi vào một thư mục "
     "giữ cuộn năm mươi file để dung lượng chiếm trên thẻ nhớ bị giới hạn.",
407: "Thông tin mạng được cấu hình một lần qua captive portal và lưu trên thiết bị, nên một "
     "lần tắt bật nguồn không đòi hỏi phải mang laptop tới.",
408: "3. Kết quả",
409: "3.1. Thu thập dữ liệu (cảm biến, cơ cấu chấp hành, bộ điều khiển)",
410: "Việc thu thập diễn ra hoàn toàn cục bộ ở tầng thiết bị. Bốn kênh cảm biến được ESP32 "
     "lấy mẫu, xử lý ngay tại đó, và phát đi kèm trạng thái hiện tại của cơ cấu chấp hành, "
     "nhờ vậy mỗi khung telemetry là một mô tả đầy đủ về khu vườn tại một thời điểm chứ "
     "không phải một tập số đo phải ghép lại về sau.",
411: "Các kênh cảm biến",
412: "Kênh", 413: "Chân", 414: "Linh kiện", 415: "Đại lượng và đơn vị",
416: "Xử lý ngay trên thiết bị",
417: "Nhiệt độ không khí", 420: "°C, một chữ số thập phân",
421: "Không; sai số ±2 °C được bàn ở dưới",
422: "Độ ẩm không khí", 425: "% độ ẩm tương đối",
426: "Không; sai số ±5 % RH",
427: "Ánh sáng môi trường", 429: "Quang trở trên ADC1", 430: "% toàn thang",
431: "Trung bình 20 mẫu liên tiếp, rồi làm mịn theo hàm mũ trọng số 0.7 cũ / 0.3 mới",
432: "Độ ẩm đất", 434: "Đầu dò điện trở trên ADC1", 435: "% toàn thang",
436: "Giá trị ADC thô được ánh xạ sang phần trăm trước khi truyền",
437: "Kênh ánh sáng cần được làm mịn vì một quang trở không lọc đặt trên ban công dao động "
     "hàng chục phần trăm khi mây và người đi qua, khiến việc xác định ngày đêm nhấp nháy "
     "liên tục. Kênh độ ẩm đất được quy đổi sang phần trăm ngay trên thiết bị thay vì trên "
     "tiến trình giám sát, để ngưỡng trong firmware và ranh giới trong ma trận hợp nhất cùng "
     "chỉ một đại lượng; nếu phép quy đổi nằm trên Raspberry Pi thì hai tầng có thể hiểu "
     "khác nhau về ý nghĩa của bốn mươi phần trăm.",
438: "Về sai số của DHT11. Độ chính xác công bố ±2 °C là đáng lưu ý vì ngưỡng phun sương đặt "
     "ở 33.0 °C. Một số đo 33.0 °C có thể ứng với bất kỳ giá trị nào từ 31 °C đến 35 °C, nên "
     "điều kiện kích hoạt phun sương không chính xác; nó được coi là một chỉ báo thô về thời "
     "tiết nóng chứ không phải một điểm đặt, còn giá trị độ ẩm chỉ dùng để hiển thị và ghi "
     "log chứ không dùng để điều khiển. Thay linh kiện này là hạng mục đầu tiên ở mục 4.2.",
439: "Các cơ cấu chấp hành",
440: "Cơ cấu chấp hành", 441: "Chân", 442: "Cách điều khiển và ràng buộc",
443: "Relay bơm tưới gốc",
445: "Active LOW. Được đóng bởi AUTO cục bộ khi dưới ngưỡng độ ẩm đất, bởi một xung khẩn cấp "
     "có thời hạn, hoặc bởi quyền thủ công của người vận hành. Khoá liên động với relay phun "
     "sương ngay trong firmware.",
446: "Relay vòi phun sương",
448: "Active LOW. Được đóng bởi AUTO cục bộ khi vượt ngưỡng nhiệt độ cao. Có thể bị cấm hoạt "
     "động độc lập với AUTO bằng một lệnh khoá sương phát ra từ ma trận hợp nhất.",
449: "Cả hai module relay đều active LOW, đây là điều thuận lợi chứ không phải ngẫu nhiên: "
     "mức chân trong lúc ESP32 khởi động tương ứng với trạng thái nhả, nên cả bơm lẫn vòi "
     "phun đều không hoạt động trong khi vi điều khiển đang khởi động.",
450: "Chính sách của bộ điều khiển cục bộ",
451: "Firmware giữ một chính sách điều khiển đầy đủ, chạy bất kể có gắn tiến trình giám sát "
     "hay không. Đây chính là mức dự phòng thứ 5 được nhắc tới xuyên suốt mục 2.",
452: "Điều kiện", 453: "Hành động", 454: "Ghi chú",
455: "Độ ẩm đất dưới 40 % và ánh sáng từ 20 % trở lên",
456: "Đóng relay tưới",
457: "Nhả ra khi số đo hồi phục. Được xét sau luật về bóng tối bên dưới, và phun sương được "
     "ưu tiên khi khay vừa khô vừa nóng",
458: "Nhiệt độ trên 33.0 °C",
459: "Đóng relay phun sương",
460: "Bị chặn khi lệnh khoá sương đang có hiệu lực",
461: "Ánh sáng dưới 20 % trong khi đất khô",
462: "Giữ nhả cả hai relay",
463: "Được xét trước luật độ ẩm, nên khay khô không bị tưới trong bóng tối. Độc lập với Time "
     "Guard theo đồng hồ của tiến trình giám sát",
464: "Nhiệt độ ngoài dải 10.0 – 38.0 °C",
465: "Phát cảnh báo",
466: "Hiện trên OLED và mang trong khung telemetry",
467: "Khung telemetry và tập lệnh",
468: "Một đối tượng JSON phân cách theo dòng được phát mỗi hai giây. Trường lý do chính là "
     "thứ cho phép dashboard giải thích trạng thái hiện tại của cơ cấu chấp hành chứ không "
     "chỉ hiển thị nó.",
469: "Trường", 470: "Kiểu", 471: "Ý nghĩa",
473: "số", 474: "Nhiệt độ không khí tính bằng °C và độ ẩm tương đối tính bằng %",
476: "số", 477: "Độ ẩm đất và ánh sáng môi trường, đều tính theo phần trăm",
479: "luận lý", 480: "Trạng thái hiện tại của relay tưới và relay phun sương",
482: "luận lý",
483: "Cho biết tiến trình giám sát có đang cấm phun sương hay không — do dòng đốm nâu của ma "
     "trận hợp nhất đặt",
485: "luận lý",
486: "Bật khi watchdog serial đã huỷ một trạng thái thủ công do tiến trình giám sát phát; "
     "hiển thị thành một băng cảnh báo trên dashboard",
488: "chuỗi",
489: "AUTO hoặc MANUAL. LOCK_IDLE được truyền về dưới dạng MANUAL với cả hai relay đều nhả; "
     "mức quyết định thực sự do tiến trình giám sát báo riêng",
491: "chuỗi",
492: "Nguyên nhân ngắn gọn, dễ đọc của trạng thái hiện tại, hiển thị nguyên văn trên dashboard",
493: "Lệnh", 494: "Tác dụng trên thiết bị",
496: "Ép relay tưới, ghi đè AUTO cục bộ trong suốt thời hạn của quyền đã cấp",
498: "Ép relay phun sương với cùng điều kiện",
500: "Cấm hoặc cho phép lại việc phun sương trong khi vẫn để việc tưới dưới AUTO cục bộ — cơ "
     "chế được dòng đốm nâu của ma trận hợp nhất sử dụng",
502: "Bỏ mọi ràng buộc và trả quyền điều khiển về cho chính sách firmware",
504: "Giữ nhả cả hai relay bất kể số đo cảm biến — dùng cho khoá ban đêm và khoá thối rễ",
506: "Nhịp tim gửi mỗi 10 giây. Không đổi trạng thái nào; chức năng duy nhất của nó là nuôi "
     "watchdog serial để một quyết định giữ lâu không bị hiểu nhầm là tiến trình giám sát đã "
     "chết",
507: "Việc tách MIST_LOCK khỏi MIST_OFF là điều đáng lưu ý. Một lệnh tắt thuần tuý là một "
     "trạng thái, và AUTO cục bộ sẽ đóng lại relay ngay ở lần đọc nóng kế tiếp; còn lệnh khoá "
     "là một ràng buộc, tồn tại cho tới khi được gỡ tường minh. Không có nó, một chẩn đoán "
     "nấm không thể được xử lý quá một chu kỳ điều khiển.",
508: "3.2. Mạng và truyền thông",
509: "Hệ thống dùng ba liên kết, và chỉ một trong số đó vượt ra khỏi phạm vi gia đình.",
510: "Liên kết", 511: "Hai đầu", 512: "Phương tiện truyền", 513: "Lưu lượng",
514: "Liên kết thiết bị", 516: "Serial USB, 115200 baud",
517: "Telemetry JSON phân cách theo dòng mỗi 2 giây; lệnh chỉ gửi khi đổi trạng thái",
518: "Liên kết dịch vụ nội bộ", 519: "Trình duyệt ↔ Raspberry Pi", 520: "HTTP cổng 5000",
521: "Dashboard hỏi REST API mỗi 3 giây; lệnh thủ công gửi khi có nhu cầu",
522: "Liên kết suy luận ra ngoài", 524: "HTTPS cổng 443",
525: "Một lần tải ảnh JPEG lên và một phản hồi JSON mỗi 15 phút",
526: "Liên kết thiết bị",
527: "Liên kết serial mang một đối tượng JSON có hình dạng cố định theo một chiều và các "
     "token lệnh ngắn theo chiều ngược lại. Ba đặc tính được bổ sung sau các sự cố quan sát "
     "được trong quá trình tích hợp. Khung hỏng bị loại riêng lẻ thay vì để nó ném ngoại lệ "
     "trong luồng đọc, vì một dòng bị cắt cụt lúc thiết bị reset không được phép làm sập cả "
     "tiến trình giám sát. Lệnh trùng liên tiếp bị chặn, nhờ vậy liên kết giữ được yên tĩnh "
     "và bảng lệnh trở thành bản ghi các lần đổi trạng thái thật. Và cổng được truy cập qua "
     "một đường thiết bị cố định do udev rule tạo ra, khớp cả cầu USB-serial CP2102 lẫn "
     "CH340, nhờ đó loại bỏ lỗi lặp đi lặp lại trong đó tên cổng đổi qua lại giữa hai giá "
     "trị sau mỗi lần khởi động và service khởi chạy nhầm thiết bị.",
528: "Cấu hình mạng và dịch vụ nội bộ",
529: "ESP32 nhận thông tin mạng qua captive portal của WiFiManager, hiện ra dưới dạng một "
     "access point mở; giữ nút BOOT ba giây sẽ xoá thông tin đã lưu và đưa thiết bị trở lại "
     "portal, nhờ vậy có thể mang khu vườn sang nhà khác mà không cần laptop. Thiết bị còn "
     "tự phục vụ một trang trạng thái nhỏ trên cổng 80, tự làm mới mỗi năm giây; sự dư thừa "
     "này là có chủ ý: nếu Raspberry Pi tắt, người trồng vẫn xem được số đo thời gian thực "
     "và điều khiển relay bằng tay.",
530: "Ứng dụng Flask gắn trên mọi giao diện mạng ở cổng 5000 để mọi thiết bị trong mạng nội "
     "bộ đều truy cập được. Nó không có xác thực, điều này chỉ chấp nhận được với giả định "
     "mạng là tin cậy; đây được nêu như một hạn chế đã biết ở mục 4.2 chứ không trình bày "
     "như một lựa chọn thiết kế.",
531: "Liên kết ra ngoài và sự cố đã quan sát được",
532: "Lưu lượng ra ngoài duy nhất là lời gọi suy luận mười lăm phút một lần. Trong quá trình "
     "phát triển, liên kết này đã hỏng với lỗi phân giải tên miền khi router đang được cấu "
     "hình lại. Hành vi quan sát được đúng như thiết kế: luồng thị giác ghi log lỗi và thử "
     "lại ở chu kỳ sau, chẩn đoán cuối hết hiệu lực, cây quyết định rơi xuống mức năm, và "
     "ESP32 tiếp tục tưới theo ngưỡng của chính nó. Không cây nào bị ảnh hưởng và không cần "
     "can thiệp thủ công. Sự cố đó là bằng chứng mạnh nhất hiện có cho lập luận ưu tiên tầng "
     "biên nêu ở mục 2.1, vì nó không phải một bài kiểm thử được dàn dựng.",
533: "Hình 3.2 — Sơ đồ triển khai và tô-pô mạng.",
534: "3.3. Hiện thực phần cứng",
535: "Bản dựng gồm một board ESP32 DevKit mang bốn cảm biến và hai module relay, đi kèm một "
     "Raspberry Pi 5 và một camera USB. Cách gán chân đã nêu ở mục 2.4; phần này ghi lại các "
     "quyết định đằng sau nó, vì nhiều lựa chọn là bắt buộc chứ không tuỳ ý.",
536: "Cả hai kênh analog đều nằm trên GPIO34 và GPIO35, thuộc ADC1. Đây là ràng buộc cứng "
     "của nền tảng chứ không phải sở thích: ADC2 không dùng được cho mã ứng dụng khi radio "
     "Wi-Fi đang hoạt động, mà thiết bị thì luôn được kỳ vọng có kết nối. Đặt đầu dò đất lên "
     "một chân ADC2 sẽ cho ra số đo chỉ hỏng sau khi mạng lên — một lỗi rất khó chẩn đoán khi "
     "thử trên bàn với board chưa nối mạng.",
537: "GPIO34 và GPIO35 là chân chỉ vào, phù hợp với các kênh cảm biến và giải phóng những "
     "chân hai chiều cho relay và bus I²C.",
538: "OLED dùng chung cặp chân I²C tiêu chuẩn GPIO21 và GPIO22 ở địa chỉ 0x3C, luân phiên "
     "hai trang trạng thái mỗi ba giây để cả số đo thời gian thực lẫn trạng thái cơ cấu chấp "
     "hành đều nhìn được mà không cần máy chủ.",
539: "Nút BOOT trên GPIO0 được tận dụng làm nút xoá cấu hình mạng. Dùng lại nút có sẵn giúp "
     "tránh phải thêm linh kiện và khoét thêm một lỗ trên vỏ hộp, và thời gian giữ ba giây "
     "đủ dài để không bị kích hoạt nhầm trong một lần reset bình thường.",
540: "Các module relay là active LOW, nên mức nghỉ được thiết lập trong lúc khởi động khiến "
     "cả bơm lẫn vòi phun đều ở trạng thái nhả. Firmware khoá liên động hai relay để chỉ một "
     "cái có thể hoạt động tại một thời điểm.",
541: "Camera được gắn trên giá cố định, cách tán lá 25–40 cm và chếch khoảng 45° từ trên "
     "xuống thay vì chụp thẳng đứng, để thân camera không đổ bóng lên lá. Khung hình cố định "
     "là điều kiện tiên quyết cho việc phát hiện điểm mù mô tả ở mục 3.5: phép kiểm tra khung "
     "hình còn chứa cây hay không chỉ có ý nghĩa nếu camera không bị kỳ vọng sẽ dịch chuyển.",
542: "Hình 3.3 — Sơ đồ gán chân và đi dây ESP32.",
543: "3.4. Trực quan hoá dữ liệu",
544: "Có hai khung nhìn: một dashboard trên trình duyệt do Raspberry Pi phục vụ, và một màn "
     "hình cục bộ trên chính thiết bị. Nguyên tắc thiết kế áp dụng xuyên suốt dashboard là "
     "không hiển thị trạng thái cơ cấu chấp hành nào mà thiếu lý do của nó, vì trong một hệ "
     "có năm mức phân xử, câu hỏi đáng quan tâm không bao giờ là bơm có đang chạy hay không "
     "mà là ai đã quyết định cho nó chạy.",
545: "Thành phần", 546: "Nguồn dữ liệu", 547: "Mục đích",
548: "Bốn thẻ cảm biến", 549: "Endpoint trạng thái thời gian thực",
550: "Nhiệt độ, độ ẩm không khí, độ ẩm đất và ánh sáng tại thời điểm hiện tại; thẻ độ ẩm đất "
     "còn được gắn thêm nhãn khô hoặc đủ ẩm so với ranh giới 40 %",
551: "Đồng hồ sức khoẻ dạng vòng", 552: "Endpoint trạng thái thời gian thực",
553: "Chẩn đoán đã kiểm chứng, kèm một nhãn tin cậy nói rõ phản hồi có được phép tác động "
     "tới cơ cấu chấp hành hay không, và một nút yêu cầu chẩn đoán ngay với cooldown 60 giây",
554: "Bảng ma trận hợp nhất", 555: "Endpoint trạng thái thời gian thực",
556: "Bảng AI × độ ẩm đất với ô khớp chẩn đoán hiện tại được tô sáng, để người vận hành thấy "
     "luật nào đang có hiệu lực",
557: "Bảng điều khiển thủ công", 558: "Endpoint lệnh",
559: "Sáu lệnh, kèm đồng hồ đếm ngược phần còn lại của thời hạn 600 giây trước khi quyền điều "
     "khiển trở về AUTO",
560: "Nhãn trạng thái", 561: "Endpoint trạng thái thời gian thực",
562: "Trạng thái tưới và phun sương, cùng chế độ firmware đang hoạt động — AUTO hoặc MANUAL — "
     "và mức quyết định của tiến trình giám sát đã sinh ra nó",
563: "Lý do quyết định", 564: "Endpoint trạng thái thời gian thực",
565: "Chuỗi lý do mang trong khung telemetry, hiển thị nguyên văn, để người vận hành phân "
     "biệt được khoá ban đêm với khoá thối rễ và với AUTO thông thường",
566: "Bốn biểu đồ sparkline", 567: "Endpoint lịch sử",
568: "Cửa sổ chọn được một giờ, sáu giờ, hai mươi bốn giờ hoặc bảy ngày cho từng kênh. Tới "
     "một giờ thì lấy từ deque trong bộ nhớ; khoảng dài hơn được truy vấn từ SQLite và lấy "
     "mẫu thưa xuống tối đa 300 điểm. Vẽ bằng đường dẫn SVG sinh ngay trong trang, không dùng "
     "thư viện biểu đồ nào",
569: "Dải ảnh", 570: "Kho ảnh",
571: "Các khung ảnh chụp gần nhất dưới dạng ảnh thu nhỏ, để có thể đối chiếu một chẩn đoán "
     "với chính tấm ảnh đã sinh ra nó",
572: "Các băng cảnh báo", 573: "Dòng sự kiện",
574: "Bốn băng độc lập: camera không thấy cây, tưới khẩn cấp hoặc khoá thối rễ kèm thời gian "
     "còn lại, phun sương đang bị cấm, và watchdog thiết bị đã kích hoạt",
575: "Dòng sự kiện và xuất CSV", 576: "Bảng sự kiện",
577: "Bản ghi theo trình tự thời gian của các chẩn đoán, lệnh và cảnh báo, xuất ra được để "
     "phân tích ngoại tuyến",
578: "Biểu đồ được vẽ bằng cách sinh thẳng dữ liệu đường dẫn SVG từ endpoint lịch sử thay vì "
     "nạp một thư viện biểu đồ. Lý do rất thực dụng: trang được phục vụ từ một máy tính nhúng "
     "tới trình duyệt điện thoại trên một mạng nội bộ có thể không có đường ra Internet, nên "
     "một trang phụ thuộc vào mạng phân phối nội dung sẽ trắng đúng vào tình huống mà hệ "
     "thống được thiết kế để vượt qua.",
579: "Khung nhìn phía thiết bị là màn hình OLED, luân phiên hai trang mỗi ba giây, cùng với "
     "trang trạng thái nhỏ mà ESP32 phục vụ trên cổng 80 và tự làm mới mỗi năm giây. Cả hai "
     "vẫn dùng được khi Raspberry Pi đã tắt.",
581: "Hình 3.4 — Dashboard web: đồng hồ đo, lý do quyết định, lịch sử cảm biến và kho ảnh.",
582: "3.5. Kiểm thử và cải tiến",
583: "Các bài kiểm chứng",
584: "Năm bài kiểm thử đã được chạy trên hệ thống tích hợp. Mỗi bài nhắm vào một sự cố đã "
     "thực sự xảy ra chứ không phải một giả định.",
585: "STT", 586: "Bài kiểm thử", 587: "Cách làm", 588: "Kết quả",
590: "Loại bỏ phản hồi không hợp lệ của mô hình",
591: "Chín phản hồi dựng sẵn được đưa vào hàm kiểm chứng — sáu phản hồi hỏng (bình thường với "
     "độ tin cậy bằng không, hai trạng thái ngoài tập cho phép, héo rũ với độ tin cậy 30, một "
     "độ tin cậy không phải số, một phản hồi thiếu trường trạng thái) và ba phản hồi hợp lệ, "
     "trong đó một phản hồi mang độ tin cậy 150 vượt khoảng",
592: "Cả sáu phản hồi hỏng đều bị hạ xuống mức không xác định; cả ba phản hồi hợp lệ đều được "
     "chấp nhận, giá trị 150 bị kẹp về 100. Không phản hồi hỏng nào chạm tới vòng lặp quyết "
     "định",
594: "Ngăn bơm chạy vô thời hạn",
595: "Sáu chu kỳ khẩn cấp liên tiếp được cho chạy qua vòng lặp quyết định",
596: "Chuỗi lệnh cho thấy xung được phát rồi được nhả khi hết hạn; quyền điều khiển trở về "
     "AUTO ở mọi lần",
598: "Chẩn đoán héo rũ khi đất còn ẩm",
599: "Bơm chẩn đoán héo rũ với độ tin cậy 95 trong khi độ ẩm đất đọc được 75 %",
600: "Hệ thống phát lệnh khoá nghỉ và không tưới — đúng hành vi đã đặc tả cho trường hợp thối rễ",
602: "Khôi phục lịch sử sau khi khởi động lại",
603: "Dừng rồi chạy lại service; quan sát quá trình nạp lại cơ sở dữ liệu",
604: "Ba mươi chín số đo đã lưu được nạp lại; biểu đồ có dữ liệu ngay thay vì bắt đầu từ trống",
606: "Tính nhất quán của giao diện",
607: "Gọi hết mười hai endpoint REST và đối chiếu từng thành phần dashboard với định danh "
     "backend mà nó tiêu thụ",
608: "Không tìm thấy định danh nào lệch",
610: "Kết xuất các thành phần dashboard có điều kiện",
611: "Dựng trang ở chế độ headless tại trạng thái biết chắc là rỗng, rồi kiểm tra style tính "
     "toán của từng phần tử mang thuộc tính hidden",
612: "Bốn băng cảnh báo, lưới biểu đồ và phần tử ảnh vẫn được kết xuất dù đang mang thuộc "
     "tính hidden, vì khai báo display của tác giả thắng mặc định của trình duyệt vốn hiện "
     "thực thuộc tính này. Đã sửa và kiểm chứng lại theo cả hai chiều",
613: "Bài T3 là bài quyết định luận điểm trung tâm của đồ án có đứng vững hay không. Một bộ "
     "điều khiển chỉ dùng độ ẩm đất, đặt vào cùng điều kiện, sẽ không làm gì cả, vì số đo 75 "
     "% là hoàn toàn khoẻ mạnh; cây sẽ tiếp tục ngồi trong đất sũng nước. Hệ thống được kiểm "
     "thử đã giữ nước lại và báo tình trạng lên cho người vận hành, đây chính là hành vi đòi "
     "hỏi phải có thị giác mới thực hiện được.",
614: "Hình 3.5 — Trình tự tưới khẩn cấp với xung có thời hạn và cooldown.",
615: "Hình 3.6 — Watchdog serial nhả cơ cấu chấp hành do tiến trình giám sát ép, sau khi "
     "nhịp tim ngừng.",
616: "Các khiếm khuyết đã phát hiện và khắc phục",
617: "Một đợt rà soát nội bộ cuối giai đoạn 4 đã xem xét hệ thống như một thiết bị gia dụng "
     "chứ không phải một bản demo, và đặt cho từng thành phần câu hỏi: điều gì sẽ xảy ra nếu "
     "để nó chạy không người trông trong một tuần. Chín khiếm khuyết được xác định, ba trong "
     "số đó đủ nghiêm trọng để chặn việc triển khai. Giai đoạn 5 được thêm vào tiến độ để "
     "khắc phục chúng.",
618: "Một đợt rà soát thứ hai sau giai đoạn 5, lần này đọc firmware và tiến trình giám sát "
     "đối chiếu với nhau thay vì đọc riêng từng bên, đã tìm thêm bốn khiếm khuyết. Một trong "
     "số đó âm thầm vô hiệu hoá khoá ban đêm, vốn là bảo đảm an toàn mạnh nhất mà hệ thống "
     "tuyên bố, nên nó được ghi ở đây với mức độ nghiêm trọng ngang các khiếm khuyết chặn "
     "triển khai ở trên.",
619: "STT", 620: "Khiếm khuyết", 621: "Cách khắc phục",
623: "Camera chĩa sai hướng vẫn cho ra kết luận bình thường một cách tự tin, nên hệ thống báo "
     "cây khoẻ trong khi đang nhìn vào một bức tường. Khiếm khuyết chặn triển khai.",
624: "Prompt nay buộc mô hình phải nói rõ có nhìn thấy cây hay không; số lần thất bại liên "
     "tiếp được đếm, một sự kiện cảnh báo camera được ghi và một băng cảnh báo hiện trên "
     "dashboard.",
626: "Kết luận bình thường mang độ tin cậy bằng không vẫn được chấp nhận, các trạng thái nằm "
     "ngoài tập cho phép cũng vậy. Khiếm khuyết chặn triển khai.",
627: "Một hàm chuẩn hoá kiểm chứng tập trạng thái và áp ngưỡng tin cậy 40 trước khi bất kỳ "
     "phản hồi nào chạm tới vòng lặp quyết định.",
629: "Bơm có thể tiếp tục chạy suốt cả cửa sổ cooldown một giờ. Khiếm khuyết chặn triển khai.",
630: "Một cơ chế xung có thời hạn dùng chung gán cho mọi lệnh ép một thời điểm hết hạn, sau "
     "đó quyền điều khiển tự trở về AUTO.",
632: "Lịch sử cảm biến chỉ tồn tại trong bộ nhớ và mất đi sau mỗi lần khởi động lại.",
633: "SQLite ở chế độ write-ahead logging, ghi mỗi 60 giây, nạp lại một giờ gần nhất khi khởi "
     "động.",
635: "Nhật ký sự kiện chỉ ghi các sự kiện AI, nên không dựng lại được lịch sử lệnh.",
636: "Bốn bảng — số đo, chẩn đoán, lệnh và sự kiện — kèm một endpoint xuất CSV.",
638: "Mỗi lần chụp lại ghi đè lên ảnh trước, nên không truy vết được một chẩn đoán về đúng "
     "khung ảnh đã sinh ra nó.",
639: "Tên file có dấu thời gian với kho cuộn năm mươi file và một dải ảnh thu nhỏ trên "
     "dashboard.",
641: "Kết quả thị giác chỉ tác động tới một trong bốn trạng thái chẩn đoán, nên phần AI phần "
     "lớn chỉ mang tính trang trí.",
642: "Ma trận hợp nhất AI × độ ẩm đất, trong đó ba ô làm thay đổi hành vi cơ cấu chấp hành.",
644: "Tiến trình được khởi động bằng tay; log cho thấy sáu lần khởi động rải rác trong suốt "
     "quá trình phát triển.",
645: "Một unit systemd với Restart=always và độ trễ khởi động lại mười giây.",
647: "Tên thiết bị serial đổi qua lại giữa hai giá trị sau mỗi lần khởi động.",
648: "Một udev rule cung cấp đường thiết bị cố định cho cả hai loại cầu USB-serial.",
650: "Watchdog trong firmware chờ một nhịp tim từ tiến trình giám sát, nhưng tiến trình giám "
     "sát chưa bao giờ gửi. Vì lệnh trùng bị chặn, một quyết định giữ nguyên không sinh ra "
     "lưu lượng serial nào, nên thiết bị đọc sự im lặng đó thành máy chủ đã chết và huỷ trạng "
     "thái. Khoá ban đêm vì vậy bị nhả ra khoảng 60 giây sau khi được áp, và việc tưới có thể "
     "tiếp diễn trong bóng tối. Khiếm khuyết chặn triển khai.",
651: "Tiến trình giám sát gửi một PING mỗi 10 giây. Nó không mang trạng thái nào và chỉ tồn "
     "tại để phân biệt một quyết định ổn định với một máy chủ đã chết. Đã kiểm chứng trên "
     "phần cứng bằng cách giữ một trạng thái ép vượt quá khoảng thời gian watchdog.",
653: "Các khung sự kiện của thiết bị, chẳng hạn thông báo watchdog, bị phân tích như "
     "telemetry và ghi đè lên tập số đo thời gian thực. Dashboard trắng số liệu và độ ẩm đất "
     "biến mất khỏi đầu vào của ma trận hợp nhất đúng vào lúc một sự cố đang được báo.",
654: "Các khung không mang trường nhiệt độ được chuyển sang nhật ký sự kiện thay vì trạng "
     "thái telemetry.",
656: "Thuộc tính hidden không có tác dụng với bất kỳ phần tử nào đồng thời mang một khai báo "
     "display, vì khai báo của tác giả thắng mặc định của trình duyệt vốn hiện thực thuộc "
     "tính này. Bốn băng cảnh báo, lưới biểu đồ rỗng và phần tử ảnh vì thế hiển thị thường "
     "trực, trong đó có một băng không chứa chữ nào.",
657: "Một luật reset khôi phục lại thuộc tính này. Đã kiểm chứng lại theo cả hai chiều trên "
     "một lần dựng trang headless: phần tử ẩn thì biến mất, và chính các phần tử đó vẫn được "
     "bố cục đúng khi hiện ra.",
659: "Ghi chú tự do của mô hình được ghi thẳng vào trang mà không escape, nên chỉ một dấu ngoặc "
     "nhọn trong ghi chú chẩn đoán cũng làm hỏng dòng sự kiện. Dấu thời gian của ảnh cũng bị "
     "đọc lệch một ký tự, hiển thị 14:30 thành _1:43.",
660: "Ghi chú được escape khi chèn; sửa lại độ lệch của dấu thời gian.",
661: "Các khiếm khuyết 1, 2 và 7 có chung một hình dạng, và nói thẳng ra thì hữu ích hơn là "
     "liệt kê riêng lẻ: ở bản đầu tiên, mô hình thị giác được tin mà không được kiểm, và được "
     "hỏi ý mà không được hành động theo. Nó không thể sai theo cách nào mà hệ thống nhận ra, "
     "và cũng không thể đúng theo cách nào có ý nghĩa. Giai đoạn 5 xử lý cả hai nửa của vấn "
     "đề đó, và ma trận hợp nhất là kết quả.",
662: "Công việc đang tiến hành",
663: "Một đợt chạy thực địa liên tục ba đến năm ngày trên khay rau thật đang được tiến hành. "
     "Mục đích là phơi ra những sự cố chỉ xuất hiện theo thời gian — đầu dò trôi giá trị, hơi "
     "nước đọng trên vỏ camera, và hành vi của kho ảnh khi chạm giới hạn lưu giữ.",
664: "Ba kịch bản minh hoạ đang được quay: tưới khẩn cấp khi héo rũ với đất khô; một lệnh thủ "
     "công bị từ chối trong khung khoá ban đêm; và phun sương bị cấm sau một chẩn đoán đốm nâu.",
665: "Độ chính xác của mô hình thị giác trên một tập khoảng 30–40 ảnh lá do nhóm tự gán nhãn "
     "vẫn đang chờ đo. Con số này được cố ý để trống thay vì ước lượng. [ CHỜ ĐO — hạng mục "
     "WBS 3.3 ]",
666: "4. Tác động dự kiến",
667: "4.1. Kết quả đạt được và lợi ích",
668: "Từng mục tiêu nêu ở mục 1.2 được đánh giá dưới đây dựa trên bằng chứng thu được trong "
     "quá trình làm đồ án.",
669: "STT", 670: "Mục tiêu", 671: "Trạng thái", 672: "Bằng chứng",
674: "Cảm nhận và tác động cục bộ với một chính sách tự chủ trên thiết bị",
675: "Đạt",
676: "Firmware giữ một chính sách theo ngưỡng đầy đủ; đã kiểm chứng là vẫn tưới khi tiến "
     "trình giám sát bị dừng",
678: "Phân xử ưu tiên tất định theo chu kỳ cố định",
679: "Đạt",
680: "Cây năm mức đánh giá lại mỗi 2 giây; mức quyết định được ghi kèm mọi lệnh",
682: "Chẩn đoán thị giác đã kiểm chứng, bị ràng buộc vào tập trạng thái",
683: "Đạt",
684: "Hàm kiểm chứng với ngưỡng tin cậy 40; bài kiểm thử T1",
686: "Ít nhất ba ô hợp nhất cho kết quả khác một hệ chỉ dùng cảm biến",
687: "Đạt",
688: "Ba ô làm đổi hành vi cơ cấu chấp hành; bài T3 minh chứng ô quyết định nhất",
690: "Lệnh ép có giới hạn thời gian và một khoá không thể ghi đè",
691: "Đạt",
692: "Cơ chế xung dùng chung; bài T2. Khoá ban đêm nằm trên quyền thủ công trong thang ưu "
     "tiên, và watchdog thiết bị cùng nhịp tim 10 giây bảo đảm một khoá đang giữ không bị "
     "thiết bị huỷ cũng không bị tiến trình giám sát bỏ quên (khiếm khuyết 10)",
694: "Sống sót qua khởi động lại, mất điện, đứt kết nối và mất Internet",
695: "Đạt",
696: "systemd tự chạy lại, đường thiết bị cố định, nạp lại cơ sở dữ liệu (bài T4), và một lần "
     "mất mạng ngoài kế hoạch được xử lý đúng như thiết kế",
698: "Toàn bộ trạng thái được phơi bày trong mạng nội bộ",
699: "Đạt",
700: "Mười hai endpoint REST, dashboard có lý do quyết định, kho ảnh, nhật ký sự kiện kèm "
     "xuất CSV (bài T5 và T6)",
701: "Lợi ích",
702: "Với người trồng, hệ thống loại bỏ thói quen kiểm tra hằng ngày và, quan trọng hơn, loại "
     "bỏ đúng sự cố mà việc kiểm tra bằng mắt không ngăn được: tưới cho một cây đang héo vì "
     "rễ của nó vốn đã úng nước. Riêng trường hợp đó là khác biệt giữa một máy tưới tự động "
     "và một hệ chăm sóc tự động.",
703: "Nước được cấp khi có nhu cầu và bị giữ lại khi đất đã đủ ẩm, còn phun sương bị chặn "
     "hoàn toàn một khi triệu chứng nấm xuất hiện — vừa là tiết kiệm vừa là biện pháp kiểm "
     "soát bệnh, vì phun sương chính là cơ chế làm bệnh đốm lá lây lan.",
704: "Hệ thống vẫn hoạt động trong lúc mất mạng. Với việc triển khai tại các hộ gia đình Việt "
     "Nam, nơi kết nối Internet dân dụng tốt nhưng không bảo đảm, một thiết bị ngừng hoạt "
     "động mỗi khi router khởi động lại sẽ không được chấp nhận.",
705: "Chính sách điều khiển có thể chuyển giao. Ma trận hợp nhất là một bảng nhỏ gồm các cặp "
     "nhãn thị giác × trạng thái đất, còn các ngưỡng firmware được gom về một khối, nên việc "
     "chuyển hệ thống sang một loại cây ngắn ngày khác chỉ là chỉnh lại giá trị chứ không "
     "phải viết lại logic.",
706: "Thiết kế này khái quát được ra ngoài phạm vi làm vườn. Khuôn mẫu được minh chứng ở đây "
     "— một cảm biến số rẻ tiền thiết lập bối cảnh, một mô hình thị giác cung cấp nhãn ngữ "
     "nghĩa, và một tầng phân xử không tin tuyệt đối bên nào — áp dụng được cho mọi bài toán "
     "giám sát trong đó phép đo vật lý chỉ là đại lượng đại diện cho tình trạng thực sự cần "
     "quan tâm.",
707: "Mức độ sẵn sàng công nghệ",
708: "Hệ thống được đánh giá ở Mức độ sẵn sàng công nghệ 5 (TRL 5): mọi thành phần đã được "
     "tích hợp, phần mềm đã được kiểm chứng trong môi trường thực tế với một số ít người dùng "
     "thật, và các định dạng dữ liệu đã được đặc tả. Chưa tuyên bố ở mức 6, vì mức đó đòi hỏi "
     "một đợt thử nghiệm thực địa hoàn chỉnh trong môi trường vận hành cùng với tài liệu hệ "
     "thống và tài liệu người dùng ban đầu; đợt chạy thực địa hỗ trợ cho tuyên bố đó đang "
     "diễn ra và dự kiến kết thúc ngay sau khi nộp báo cáo.",
709: "4.2. Hướng cải tiến",
710: "Những hạn chế sau đây đã được biết và được ghi lại ở đây thay vì để người khác phát "
     "hiện. Chúng được sắp theo mức độ nghiêm trọng của hậu quả nếu hệ thống được triển khai "
     "nguyên trạng.",
711: "STT", 712: "Hạn chế", 713: "Hậu quả", 714: "Hướng khắc phục",
716: "Endpoint lệnh không có xác thực",
717: "Bất kỳ thiết bị nào trong mạng nội bộ đều có thể đóng bơm",
718: "Xác thực bằng token cho các endpoint làm đổi trạng thái, phần chỉ đọc để mở",
720: "Chẩn đoán thị giác phụ thuộc vào kết nối Internet ra ngoài",
721: "Khi mất mạng, hệ thống suy giảm về điều khiển thuần theo ngưỡng; đã quan sát thấy trên "
     "thực tế dưới dạng lỗi phân giải tên miền",
722: "Đánh giá một bộ phân loại nhỏ chạy ngay trên thiết bị làm phương án dự phòng cho hai "
     "trường hợp héo rũ và đốm nâu",
724: "DHT11 có sai số ±2 °C và ±5 % RH",
725: "Ngưỡng phun sương 33.0 °C là thô và độ ẩm không dùng được để điều khiển",
726: "Thay bằng DHT22 hoặc SHT31 trong mọi bản dựng không còn là mẫu thử",
728: "Đầu dò độ ẩm đất là loại điện trở",
729: "Điện cực bị ăn mòn làm suy giảm số đo chỉ sau vài tuần ngâm liên tục",
730: "Thay bằng đầu dò điện dung; phần mềm không cần sửa vì số đo đã được chuẩn hoá ngay trên "
     "thiết bị",
732: "Không có bón phân tự động",
733: "Thiếu đạm được báo nhưng hệ thống không thể khắc phục",
734: "Thêm một bơm định lượng và mở rộng ma trận hợp nhất để dòng vàng lá trở thành một "
     "trường hợp có tác động thật",
736: "Chưa đo độ chính xác của mô hình trên một tập có gán nhãn",
737: "Ngưỡng tin cậy 40 và ngưỡng khẩn cấp 70 là kết quả suy luận chứ chưa phải hiệu chỉnh",
738: "Hoàn tất việc đánh giá trên tập tự gán nhãn và chỉnh lại cả hai ngưỡng theo tỷ lệ lỗi "
     "thu được",
740: "Một camera phụ trách một khay",
741: "Thiết kế không mở rộng được cho lắp đặt nhiều khay",
742: "Hỗ trợ nhiều nguồn ảnh với trạng thái riêng cho từng khay, hoặc một camera quét theo "
     "quỹ đạo cố định",
744: "Không có thông báo đẩy",
745: "Một cảnh báo camera hay một lần khoá thối rễ chỉ hiện ra với người mở dashboard",
746: "Gửi cảnh báo tới một dịch vụ nhắn tin như Telegram hoặc Zalo cho những sự kiện người "
     "trồng buộc phải xử lý",
747: "5. Nhận xét của thành viên",
749: "HỌ VÀ TÊN", 750: "NHẬN XÉT",
751: "[ Tên nhóm trưởng ]", 752: "[ Thành viên 2 ]", 753: "[ Thành viên 3 ]",
754: "[ Thành viên 4 ]",
755: "6. Nhận xét của giảng viên",
756: "HẠNG MỤC", 757: "ĐIỂM", 758: "NHẬN XÉT",
759: "Ý TƯỞNG", 761: "ỨNG DỤNG", 763: "KẾT QUẢ",
765: "QUẢN LÝ ĐỒ ÁN", 767: "THUYẾT TRÌNH & BÁO CÁO", 769: "TỔNG",
}


def set_text(el, new):
    ts = list(el.iter(qn('w:t')))
    if not ts:
        return False
    ts[0].text = new
    ts[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    for t in ts[1:]:
        t.text = ''
    return True


def main():
    orig = json.load(open(EXTRACT, encoding='utf-8'))
    d = docx.Document(str(SRC))

    # Duyet lai dung thu tu nhu luc trich xuat.
    targets = []
    for el in d.element.body:
        if el.tag == qn('w:p'):
            if ''.join(n.text or '' for n in el.iter(qn('w:t'))).strip():
                targets.append(('P', el, None))
        elif el.tag == qn('w:tbl'):
            for tr in el.findall(qn('w:tr')):
                for tc in tr.findall(qn('w:tc')):
                    ps = [p for p in tc.findall(qn('w:p'))
                          if ''.join(n.text or '' for n in p.iter(qn('w:t'))).strip()]
                    if ps:
                        targets.append(('C', ps[0], ps[1:]))

    if len(targets) != len(orig):
        print(f'LECH: tim thay {len(targets)} don vi nhung file trich co {len(orig)}')
        return

    lech, doi = [], 0
    for i, (kind, el, extra) in enumerate(targets):
        cur = ''.join(n.text or '' for n in el.iter(qn('w:t')))
        goc = orig[i][4]
        if kind == 'P' and cur.strip() != goc.strip():
            lech.append(i)
            continue
        if i in T:
            set_text(el, T[i])
            for p in (extra or []):
                for t in p.iter(qn('w:t')):
                    t.text = ''
            doi += 1

    d.save(str(OUT))
    tong = len(orig)
    print(f'don vi van ban   : {tong}')
    print(f'da dich          : {doi}')
    print(f'giu nguyen       : {tong - doi}  (dinh danh ma nguon, so, don vi, ma O/T/M)')
    if lech:
        print(f'CANH BAO lech chi so tai: {lech[:10]}')


if __name__ == '__main__':
    main()
