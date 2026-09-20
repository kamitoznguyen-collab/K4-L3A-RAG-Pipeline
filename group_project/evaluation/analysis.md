| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Prepend tiêu đề tài liệu vào nội dung từng chunk (contextual chunking) thay vì chỉ để nó ở chunk đầu | Với câu "điều kiện xét học bổng KKHT của UET", chunk chứa đáp án (`hoc-bong-uet-2025-2026.md::chunk-1`) **không lọt top-40 của dense**, trong khi BM25 xếp nó hạng 3. Chunk đó chỉ liệt kê "Khá trở lên", "Giỏi trở lên", "15 tín chỉ" — không có từ khoá chủ đề nào để dense nối với câu hỏi. Tên tài liệu chỉ xuất hiện ở chunk-0. Thí nghiệm ở bảng Bonus bên dưới củng cố giả thuyết này: khi **bỏ bớt** phần text chứa tiêu đề ra khỏi chunk, điểm Config B tụt từ 0.745 xuống 0.527 | Giảm số câu bị từ chối vì không tìm được chunk (hiện A 6/15, B 2/15). Đây là điểm nghẽn lớn nhất của hệ thống | Chạy lại `eval_pipeline.py`, đếm lại số câu có điểm 0.000 trong `per_question_scores.json` và so Context recall với mức hiện tại (A 0.600 / B 0.867) |
| 2 | Nới số ứng viên đưa vào RRF (hiện `top_k*2`) hoặc nâng `top_k` từ 5 lên 7 | Cũng ở câu UET: sau khi fuse, chunk chứa đáp án xếp **hạng 6** — trượt `top_k=5` đúng một bậc. Lý do là RRF cộng điểm theo thứ hạng nên ưu tiên chunk xuất hiện ở **cả hai** danh sách; chunk này chỉ có mặt trong danh sách BM25 nên chỉ được 1/63, thua các chunk kém liên quan hơn nhưng góp mặt ở cả hai bên | Cứu được nhóm câu mà đúng một ranker tìm ra — chính là nhóm mà hybrid sinh ra để phục vụ | So Context recall trước/sau. Cần cẩn thận: nâng `top_k` kéo thêm chunk nhiễu nên Context precision (đang 0.490) có thể giảm |
| 3 | Mở rộng golden dataset lên 30–40 câu, phủ đều cả 10 tài liệu | Điểm từng câu **phân cực hoàn toàn**: hoặc ~0.8–1.0, hoặc đúng 0.000, không có giá trị trung gian. 0.000 luôn là do pipeline từ chối trả lời vì thiếu chunk. Với 15 câu, mỗi câu đổi trạng thái làm average dịch ~0.06, nên chênh lệch nhỏ không đọc được. Tài liệu `hoc-bong-dinh-thien-ly.md` (dài nhất, 17KB) hiện chưa có câu hỏi nào | A/B và mọi thí nghiệm sau đó có độ phân giải đủ để kết luận | Lặp lại A/B trên dataset mới; chênh lệch đáng tin khi nó lớn hơn dao động giữa hai lần chạy (đo được ~0.01, xem Bonus) |

**Hybrid không thắng tuyệt đối.** Câu 14 (học bổng JAIF của VJU) đi ngược xu hướng:
Config A đạt 0.853 còn Config B bị 0.000. RRF đã đẩy chunk mà dense tìm đúng ra
khỏi top-5. Kết luận "hybrid tốt hơn" đúng ở mức trung bình (+0.220) chứ không
đúng với từng câu.

**Điểm 0.000 không phải hallucination.** Mọi case 0.000 đều là safe refusal —
pipeline không tìm được chunk nên trả về "Tôi không thể xác minh thông tin này
từ nguồn hiện có" thay vì bịa. Ragas chấm refusal bằng 0 ở cả 4 metric, nên điểm
thấp ở đây phản ánh **recall của retrieval**, không phải độ trung thực của LLM.

**Độ tin cậy của bảng điểm.** Corpus 10 tài liệu / 88 chunk vẫn nhỏ, và golden
dataset được soạn từ chính corpus đó nên điểm có thiên lệch lạc quan. Con số dùng
được để so sánh giữa các cấu hình, không dùng để tuyên bố chất lượng tuyệt đối.
