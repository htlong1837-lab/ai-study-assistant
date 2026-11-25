# Bật "Đăng nhập bằng Google" cho trang Hộp thư

Người dùng chỉ bấm **Đăng nhập bằng Google**, chọn tài khoản và đồng ý cho DP xem email. Để nút
này chạy, người cài app phải tạo khóa OAuth trên Google **một lần** (khoảng 10 phút). Khóa là của
người cài, nên người cài tự đăng nhập Google Cloud và tự tạo; không đưa khóa cho người khác và không
commit file khóa.

## 1. Tạo dự án và bật Gmail API

1. Vào https://console.cloud.google.com/, tạo dự án mới (ví dụ `dp-daily-planner`).
2. **APIs & Services → Library**, tìm **Gmail API**, bấm **Enable**.

## 2. Màn hình xin quyền (OAuth consent screen)

1. **APIs & Services → OAuth consent screen** (bản mới gọi là **Google Auth Platform**).
2. Loại người dùng: **External**. Điền tên app `DP · Daily Planner` (logo: `assets/logo.png`), email hỗ trợ, email liên hệ.
3. **Data access / Scopes:** thêm `.../auth/gmail.readonly` (chỉ đọc thư), cùng `openid`, `email`,
   `profile`.
4. **Audience / Test users:** để ở chế độ **Testing** và thêm Gmail của những người sẽ dùng thử
   (tối đa 100 người, ví dụ cả nhóm và thầy cô chấm).

`gmail.readonly` là quyền "hạn chế" của Google. Ở chế độ Testing, Google hiện cảnh báo "Google chưa
xác minh ứng dụng này"; người dùng bấm **Tiếp tục**. Muốn mở cho mọi người thì phải gửi Google xét
duyệt và kiểm định bảo mật, không cần cho đồ án.

## 3. Tạo khóa OAuth

1. **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Loại: **Web application**.
3. **Authorized redirect URIs:** thêm `http://localhost:8501/oauth2callback` (chạy ở cổng khác thì
   đổi số cổng; triển khai lên mạng thì thêm `https://<địa-chỉ-app>/oauth2callback`).
4. Bấm **Create**, chép **Client ID** và **Client secret**.

## 4. Điền vào app

```powershell
Copy-Item .streamlit/secrets.example.toml .streamlit/secrets.toml
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Mở `.streamlit/secrets.toml`, điền `client_id`, `client_secret` và dán chuỗi ngẫu nhiên vừa in vào
`cookie_secret`. Kiểm tra `redirect_uri` khớp đúng địa chỉ ở bước 3. File này đã nằm trong
`.gitignore`.

Cài thư viện rồi chạy lại app:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Cách hoạt động

- Đăng nhập do Streamlit (`st.login`, thư viện Authlib) và Google xử lý; app không thấy mật khẩu.
- Sau khi đăng nhập, app lấy mã truy cập (`st.user.tokens["access"]`) và gọi Gmail API đọc tối đa 20
  thư trong 14 ngày gần nhất ở Hộp thư đến (`modules/email_security/gmail.py`). Không gửi, xoá hay
  sửa thư.
- Mỗi thư đi qua đúng bộ quét như file `.eml`: phân loại, quét link và tệp, chặn email độc.
- Mã truy cập sống khoảng 1 giờ. Hết hạn thì app báo đăng nhập lại.
- **Đăng xuất** xoá phiên đăng nhập. Muốn thu hồi hẳn quyền: https://myaccount.google.com/permissions.

## Không có khóa thì sao

Nút vẫn hiện nhưng bấm sẽ báo app chưa được bật đăng nhập Google. Vẫn dùng được mục **Cách khác**:
email Yahoo/iCloud bằng mật khẩu ứng dụng, tải file `.eml`, hoặc **Email mẫu** cho buổi demo.
