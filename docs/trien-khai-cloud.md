# Đưa DP lên mạng (Streamlit Community Cloud)

Sau khi làm xong, ai cũng mở được DP bằng một link cố định dạng `https://<tên>.streamlit.app`, đăng
nhập Google, và mỗi người có lịch riêng. Miễn phí. Người làm cần một tài khoản GitHub có quyền với
repo `htlong1837-lab/ai-study-assistant`.

## Dữ liệu sống sót qua khởi động lại thế nào

Community Cloud xoá ổ đĩa mỗi khi app khởi động lại (đẩy code mới, hoặc app "ngủ" vì lâu không ai
dùng). DP vì thế sao lưu lịch của mỗi người vào **một tệp trong Google Drive của chính người đó**
(`DP - Daily Planner (du lieu).zip`, quyền `drive.file`: DP chỉ thấy tệp do DP tạo) sau mỗi thay đổi,
và lấy lại khi họ đăng nhập (`modules/storage/drive_sync.py`). Khách chưa đăng nhập chỉ có dữ liệu mẫu
tạm thời.

## 1. Google Cloud: bật Drive và thêm quyền (làm một lần)

1. **APIs & Services → Library → Google Drive API → Enable.**
2. **Google Auth Platform → Data Access → Add or remove scopes:** thêm
   `https://www.googleapis.com/auth/drive.file`, **Update**, **Save**.

## 2. Tạo app trên Streamlit Community Cloud

1. Vào https://share.streamlit.io, đăng nhập bằng GitHub (tự đăng nhập; lần đầu GitHub hỏi cho phép
   Streamlit đọc repo).
2. **Create app → Deploy a public app from GitHub:**
   - Repository: `htlong1837-lab/ai-study-assistant`, Branch: `main`, Main file path: `app.py`.
   - **App URL:** chọn tên, ví dụ `dp-daily-planner` → link sẽ là `https://dp-daily-planner.streamlit.app`.
3. **Advanced settings:**
   - Python version: **3.12** hoặc **3.13**.
   - **Secrets:** dán nội dung file `.streamlit/secrets.cloud.toml` trên máy (file này không được
     commit; nếu chưa có thì chép `secrets.toml` và sửa như mục 4).
4. Bấm **Deploy**. Lần đầu cài thư viện mất vài phút.

## 3. Google Cloud: thêm địa chỉ mới

**Google Auth Platform → Clients →** OAuth client của DP **→ Authorized redirect URIs → Add URI:**

```
https://<tên-app>.streamlit.app/oauth2callback
```

Giữ lại dòng `http://localhost:8501/oauth2callback` để vẫn chạy được trên máy. Bấm **Save**, đợi vài
phút để Google cập nhật.

## 4. Secrets trên Cloud khác bản trên máy ở đâu

| Mục | Trên máy (`secrets.toml`) | Trên Cloud |
|---|---|---|
| `redirect_uri` | `http://localhost:8501/oauth2callback` | `https://<tên-app>.streamlit.app/oauth2callback` |
| `cookie_secret` | chuỗi ngẫu nhiên | nên dùng một chuỗi ngẫu nhiên khác |
| `client_id`, `client_secret`, `scope` | giống nhau | giống nhau |
| `GEMINI_API_KEY`, `VIRUSTOTAL_API_KEY` | ở `.env` | đặt ở **đầu** secrets (ngoài mọi mục `[...]`) nếu muốn bật AI |

Đổi secrets sau này: trên share.streamlit.io, mở app → **⋮ → Settings → Secrets**, sửa rồi **Save**
(app tự khởi động lại).

## Giới hạn cần biết

- App ngủ sau vài ngày không ai mở; người vào đầu tiên bấm "Yes, get this app back up" và đợi khoảng
  một phút.
- Tài nguyên miễn phí có hạn (RAM khoảng 1 GB): đủ cho đồ án và vài chục người dùng thử.
- Mã truy cập Google sống khoảng 1 giờ; quá giờ thì DP báo chưa lưu được vào Drive và người dùng đăng
  nhập lại.
- Tệp đính kèm email không được sao lưu (lấy lại được từ Gmail).
