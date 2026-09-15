# Machine Learning Systems — Bản dịch tiếng Việt (Tập I)

Bản dịch tiếng Việt của cuốn **[Machine Learning Systems](https://mlsysbook.ai)** (Harvard · MIT Press),
thực hiện với sự đồng ý của tác giả, nhằm **đóng góp cho cộng đồng** học và làm kỹ thuật ML ở Việt Nam.

> Đây là **Tập I – Nhập môn Hệ thống Học máy** (Introduction to Machine Learning Systems).
> Bản dịch máy có bảng thuật ngữ thống nhất, **chưa hiệu đính toàn diện** — hoan nghênh mọi góp ý.


## 🌐 Đọc online

**Website đầy đủ (điều hướng, tìm kiếm, sơ đồ, callout):** https://donamvn.github.io/mlsysbook-vi/

## 📥 Bản tải offline

> Bản tải **PDF / EPUB / DOCX** đang **tạm dừng** trong khi chờ tác giả rà soát. Trong thời gian này, mời bạn **đọc trực tuyến** tại website ở trên. Cảm ơn bạn đã quan tâm!

| Định dạng | Dùng cho | Tải |
|---|---|---|
| **HTML** | Mở bằng trình duyệt (tự chứa, kèm ảnh) | [MLSystems-TapI-vi.html](https://github.com/donamvn/mlsysbook-vi/releases/latest/download/MLSystems-TapI-vi.html) |

## Nội dung đã dịch

- **Văn xuôi:** 16 chương chính, các phụ lục và phần đầu sách. Giữ nguyên mã, công thức, trích dẫn,
  tham chiếu chéo và toàn bộ cấu trúc Quarto (`.qmd`).
- **Sơ đồ SVG:** 103 hình — dịch nhãn chữ ngay trong XML nên nét vẽ giữ nguyên, sắc, sửa được.
- **Sơ đồ raster:** 3 hình đơn giản đã dịch nhãn.
- **Chưa dịch (giữ tiếng Anh):** ảnh chụp, biểu đồ dữ liệu, và sơ đồ phức tạp có nội dung minh hoạ
  bằng tiếng Anh — để tránh làm sai ý; phần chú thích trong bài đã có tiếng Việt.

## Cấu trúc kho

```
books/vol1/      Bản dịch .qmd + các hình đã dịch (overlay lên bản gốc)
glossary/        Bảng thuật ngữ Anh–Việt dùng khi dịch
tools/pipeline/  Mã quy trình dịch (tách Quarto, dịch văn xuôi, dịch nhãn SVG/ảnh)
```

Kho này chỉ chứa **phần đã thay đổi**. Các hình không có ở đây giữ nguyên như
[bản gốc](https://github.com/harvard-edge/cs249r_book) (ghim ở commit `156fe8f`). Để dựng sách hoàn
chỉnh, phủ thư mục `books/vol1` này lên bản gốc rồi build bằng Quarto.

## Ghi công & giấy phép

Tác phẩm gốc © nhóm tác giả *Machine Learning Systems* (Vijay Janapa Reddi và cộng sự, Harvard).
Bản dịch © 2026 Đỗ Nam. Cả hai theo **CC BY-NC-SA 4.0**. Xem [NOTICE.md](NOTICE.md) và [LICENSE.md](LICENSE.md).

## Góp ý

Rất mong cộng đồng mở issue/PR để sửa thuật ngữ, câu chữ, hoặc hình còn thiếu. Mục tiêu là một
bản dịch chất lượng để gửi lại nhóm tác giả và phục vụ người học Việt Nam.
