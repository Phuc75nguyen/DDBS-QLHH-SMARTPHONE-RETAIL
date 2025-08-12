"""
Streamlit web application for distributed inventory management.

This app implements the core functionality required by the course project:

* Role‑based authentication with three user groups (CongTy, ChiNhanh, User).
* Separate data stores for each branch with MongoDB (or mongomock fallback).
* CRUD interfaces for employees (Nhanvien), materials (Vattu) and warehouses
  (Kho) with appropriate branch filtering.
* Placeholder pages for orders and receipts; these can be extended during
  later development to support full subform handling of order lines and
  quantity checks.

The application stores all user accounts and shared reference tables on
`server3`. Transactions (orders and receipts) live on server1 or server2
depending on the branch. When no connection URIs are provided, the
`DatabaseManager` uses in‑memory mongomock databases so the app can be run
without a MongoDB server.

To start the app, run:

```
streamlit run app.py
```

You should see a login screen. Use the default accounts created in the
bootstrap section (e.g. username `admin`, password `admin`) to log in.

"""

import streamlit as st  # type: ignore
from typing import List, Dict, Any

from database import DatabaseManager
import auth


def bootstrap_users(dbm: DatabaseManager) -> None:
    """Create a handful of initial accounts for demonstration.

    If the `users` collection is empty, this function inserts three users:
    * admin – a CongTy user that can view reports and manage accounts.
    * cn1_mgr – a ChiNhanh user for branch CN1 that can manage data for CN1.
    * cn2_mgr – a ChiNhanh user for branch CN2 that can manage data for CN2.
    * user1 – a User role for branch CN1 with limited rights.

    This helper is idempotent: it only runs when there are no existing users.
    """
    users_col = dbm.get_collection(None, "users")
    if users_col.count_documents({}) == 0:
        auth.create_user(dbm, "admin", "admin", "CongTy")
        auth.create_user(dbm, "cn1_mgr", "password", "ChiNhanh", branch="CN1")
        auth.create_user(dbm, "cn2_mgr", "password", "ChiNhanh", branch="CN2")
        auth.create_user(dbm, "user1", "password", "User", branch="CN1")


def main() -> None:
    # Configure page and session
    st.set_page_config(page_title="Quản lý nhập/xuất hàng hóa", page_icon="📦", layout="wide")

    # Initialize database manager and seed data if necessary
    dbm = DatabaseManager()
    dbm.init_schema()
    dbm.seed_demo_data()
    bootstrap_users(dbm)

    if "user" not in st.session_state:
        st.session_state.user = None

    def logout() -> None:
        """Clear the logged‑in user and force a rerun."""
        st.session_state.user = None
        #st.experimental_rerun()
        st.rerun()

    if st.session_state.user is None:
        # Show login form
        st.title("Đăng nhập hệ thống")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng nhập")
            if submitted:
                user_doc = auth.authenticate(dbm, username, password)
                if user_doc:
                    st.session_state.user = user_doc
                    st.success("Đăng nhập thành công!")
                    #st.experimental_rerun()
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu")
        st.stop()

    # At this point the user is authenticated
    user = st.session_state.user
    st.sidebar.write(f"Xin chào, **{user['username']}**")
    st.sidebar.write(f"Quyền: **{user['role']}**")
    if user.get("branch"):
        st.sidebar.write(f"Chi nhánh: **{user['branch']}**")
    st.sidebar.button("Đăng xuất", on_click=logout)

    # Determine accessible branch (None means view all)
    user_role = user["role"].capitalize()
    user_branch = user.get("branch")

    # Navigation menu
    menu_options: List[str] = []
    menu_options.append("Tổng quan")
    # Employees accessible to ChiNhanh and CongTy
    menu_options.append("Nhân viên")
    menu_options.append("Kho")
    menu_options.append("Vật tư")
    menu_options.append("Đơn hàng")
    menu_options.append("Phiếu nhập/xuất")
    if user_role == "Congty" or user_role == "Chinhanh":
        menu_options.append("Tạo tài khoản")
    if user_role == "Congty":
        menu_options.append("Báo cáo")

    selection = st.sidebar.selectbox("Chức năng", menu_options)

    if selection == "Tổng quan":
        show_dashboard(dbm, user)
    elif selection == "Nhân viên":
        show_employees(dbm, user)
    elif selection == "Kho":
        show_warehouses(dbm, user)
    elif selection == "Vật tư":
        show_materials(dbm, user)
    elif selection == "Đơn hàng":
        show_orders(dbm, user)
    elif selection == "Phiếu nhập/xuất":
        show_receipts(dbm, user)
    elif selection == "Tạo tài khoản":
        show_create_account(dbm, user)
    elif selection == "Báo cáo":
        show_reports(dbm, user)


def show_dashboard(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """Display a simple overview for the current user."""
    st.header("Tổng quan")
    role = user["role"].capitalize()
    if role == "Congty":
        st.write(
            "Bạn đang đăng nhập với quyền Công Ty. Bạn có thể xem dữ liệu của "
            "hai chi nhánh, tạo tài khoản mới và xem báo cáo."
        )
    elif role == "Chinhanh":
        st.write(
            f"Bạn đang đăng nhập với quyền Chi Nhánh {user.get('branch')}. "
            "Bạn có thể quản lý dữ liệu của chi nhánh này và tạo tài khoản cho "
            "nhân viên và người dùng."
        )
    else:
        st.write(
            f"Bạn đang đăng nhập với quyền User của chi nhánh {user.get('branch')}. "
            "Bạn chỉ có quyền cập nhật dữ liệu của chi nhánh này."
        )


def show_employees(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """Employee management page."""
    st.header("Danh sách nhân viên")
    branch = user.get("branch")
    role = user["role"].capitalize()
    nhanvien_col = dbm.get_collection(None, "Nhanvien")
    # Fetch employees of this branch only
    query = {"MACN": branch} if branch and role != "Congty" else {}
    employees = list(nhanvien_col.find(query))
    # Show table
    if employees:
        # Remove internal id for display
        df = [
            {
                "MANV": nv.get("MANV"),
                "Họ": nv.get("HO"),
                "Tên": nv.get("TEN"),
                "Địa chỉ": nv.get("DIACHI"),
                "Ngày sinh": nv.get("NGAYSINH"),
                "Lương": nv.get("LUONG"),
                "Chi nhánh": nv.get("MACN"),
            }
            for nv in employees
        ]
        st.dataframe(df)
    else:
        st.info("Chưa có nhân viên nào trong danh sách.")

    # Only Congty or ChiNhanh roles can modify employees
    if role in {"Congty", "Chinhanh"}:
        st.subheader("Thêm/Sửa nhân viên")
        with st.form("employee_form"):
            manv = st.text_input("Mã nhân viên")
            ho = st.text_input("Họ")
            ten = st.text_input("Tên")
            diachi = st.text_input("Địa chỉ")
            ngaysinh = st.date_input("Ngày sinh")
            luong = st.number_input("Lương", min_value=0.0, step=100.0)
            # Branch selection depends on role
            macn_options = ["CN1", "CN2"]
            selected_branch = (
                st.selectbox("Chi nhánh", macn_options) if role == "Congty" else branch
            )
            submit = st.form_submit_button("Lưu")
            if submit:
                # Convert date to ISO string
                ngaysinh_str = ngaysinh.isoformat()
                doc = {
                    "MANV": manv.strip().upper(),
                    "HO": ho.strip(),
                    "TEN": ten.strip(),
                    "DIACHI": diachi.strip(),
                    "NGAYSINH": ngaysinh_str,
                    "LUONG": float(luong),
                    "MACN": selected_branch,
                }
                # Upsert (insert or update) employee
                existing = nhanvien_col.find_one({"MANV": doc["MANV"]})
                if existing:
                    nhanvien_col.update_one({"MANV": doc["MANV"]}, {"$set": doc})
                    st.success("Cập nhật nhân viên thành công")
                else:
                    nhanvien_col.insert_one(doc)
                    st.success("Thêm nhân viên mới thành công")
                #st.experimental_rerun()
                st.rerun()

        # Delete employee section
        st.subheader("Xóa nhân viên")
        manv_to_delete = st.text_input("Nhập mã nhân viên cần xóa")
        if st.button("Xóa"):
            if nhanvien_col.delete_one({"MANV": manv_to_delete.strip().upper()}).deleted_count:
                st.success("Đã xóa nhân viên")
            else:
                st.error("Không tìm thấy nhân viên hoặc lỗi khi xóa")
           #st.experimental_rerun()
            st.rerun()


def show_warehouses(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """Warehouse management page."""
    st.header("Danh sách kho")
    branch = user.get("branch")
    role = user["role"].capitalize()
    kho_col = dbm.get_collection(None, "Kho")
    query = {"MACN": branch} if branch and role != "Congty" else {}
    warehouses = list(kho_col.find(query))
    if warehouses:
        df = [
            {
                "MAKHO": k.get("MAKHO"),
                "Tên kho": k.get("TENKHO"),
                "Địa chỉ": k.get("DIACHI"),
                "Chi nhánh": k.get("MACN"),
            }
            for k in warehouses
        ]
        st.dataframe(df)
    else:
        st.info("Chưa có kho nào trong danh sách.")

    if role in {"Congty", "Chinhanh"}:
        st.subheader("Thêm/Sửa kho")
        with st.form("warehouse_form"):
            makho = st.text_input("Mã kho")
            tenkho = st.text_input("Tên kho")
            diachi = st.text_input("Địa chỉ")
            selected_branch = (
                st.selectbox("Chi nhánh", ["CN1", "CN2"]) if role == "Congty" else branch
            )
            submit = st.form_submit_button("Lưu")
            if submit:
                doc = {
                    "MAKHO": makho.strip().upper(),
                    "TENKHO": tenkho.strip(),
                    "DIACHI": diachi.strip(),
                    "MACN": selected_branch,
                }
                existing = kho_col.find_one({"MAKHO": doc["MAKHO"]})
                if existing:
                    kho_col.update_one({"MAKHO": doc["MAKHO"]}, {"$set": doc})
                    st.success("Cập nhật kho thành công")
                else:
                    kho_col.insert_one(doc)
                    st.success("Thêm kho mới thành công")
                #st.experimental_rerun()
                st.rerun()

        st.subheader("Xóa kho")
        makho_to_delete = st.text_input("Nhập mã kho cần xóa")
        if st.button("Xóa kho"):
            if kho_col.delete_one({"MAKHO": makho_to_delete.strip().upper()}).deleted_count:
                st.success("Đã xóa kho")
            else:
                st.error("Không tìm thấy kho hoặc lỗi khi xóa")
            #st.experimental_rerun()
            st.rerun()


def show_materials(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """Materials management page."""
    st.header("Danh mục vật tư")
    role = user["role"].capitalize()
    vattu_col = dbm.get_collection(None, "Vattu")
    materials = list(vattu_col.find())
    if materials:
        df = [
            {
                "MAHANG": vt.get("MAHANG"),
                "Tên hàng": vt.get("TENHANG"),
                "Đơn vị tính": vt.get("DVT"),
            }
            for vt in materials
        ]
        st.dataframe(df)
    else:
        st.info("Chưa có vật tư nào trong danh sách.")

    if role in {"Congty", "Chinhanh"}:
        st.subheader("Thêm/Sửa vật tư")
        with st.form("material_form"):
            mahang = st.text_input("Mã hàng")
            tenhang = st.text_input("Tên hàng")
            dvt = st.text_input("Đơn vị tính")
            submit = st.form_submit_button("Lưu")
            if submit:
                doc = {
                    "MAHANG": mahang.strip().upper(),
                    "TENHANG": tenhang.strip(),
                    "DVT": dvt.strip(),
                }
                existing = vattu_col.find_one({"MAHANG": doc["MAHANG"]})
                if existing:
                    vattu_col.update_one({"MAHANG": doc["MAHANG"]}, {"$set": doc})
                    st.success("Cập nhật vật tư thành công")
                else:
                    vattu_col.insert_one(doc)
                    st.success("Thêm vật tư mới thành công")
                #st.experimental_rerun()
                st.rerun()

        st.subheader("Xóa vật tư")
        mahang_to_delete = st.text_input("Nhập mã vật tư cần xóa")
        if st.button("Xóa vật tư"):
            if vattu_col.delete_one({"MAHANG": mahang_to_delete.strip().upper()}).deleted_count:
                st.success("Đã xóa vật tư")
            else:
                st.error("Không tìm thấy vật tư hoặc lỗi khi xóa")
            #st.experimental_rerun()
            st.rerun()


def show_orders(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """Orders management page (Đơn hàng)."""
    st.header("Đơn đặt hàng")
    role = user["role"].capitalize()
    branch = user.get("branch")
    # Determine collection and underlying client based on branch
    dathang_col = dbm.get_collection(branch, "DatHang") if branch else None
    ctddh_col = dbm.get_collection(branch, "CTDDH") if branch else None
    # Select the correct MongoClient so we can start a session for writes
    client = None
    if branch == "CN1":
        client = dbm.client_server1
    elif branch == "CN2":
        client = dbm.client_server2

    if role == "Congty":
        st.info("Chức năng này hiện chưa hỗ trợ cho quyền Công Ty.")
        return
    # Show list of orders for the user's branch
    orders = list(dathang_col.find({})) if dathang_col else []
    if orders:
        df = [
            {
                "Mã đơn": dh.get("MasoDDH"),
                "Ngày": dh.get("NGAY"),
                "Nhà CC": dh.get("NhaCC"),
                "Mã NV": dh.get("MANV"),
                "Mã kho": dh.get("MAKHO"),
            }
            for dh in orders
        ]
        st.dataframe(df)
    else:
        st.info("Chưa có đơn hàng nào.")

    # Only branch managers/users can add orders
    st.subheader("Tạo đơn đặt hàng mới")
    with st.form("order_form"):
        masoddh = st.text_input("Mã đơn đặt hàng")
        ngay = st.date_input("Ngày lập đơn")
        nhacc = st.text_input("Nhà cung cấp")
        # Employee must be within branch
        nhanvien_col = dbm.get_collection(None, "Nhanvien")
        nhanvien_list = list(nhanvien_col.find({"MACN": branch}))
        manv_options = [nv["MANV"] for nv in nhanvien_list]
        manv = st.selectbox("Nhân viên lập", manv_options) if manv_options else ""
        kho_col = dbm.get_collection(None, "Kho")
        kho_list = list(kho_col.find({"MACN": branch}))
        makho_options = [k["MAKHO"] for k in kho_list]
        makho = st.selectbox("Kho nhập", makho_options) if makho_options else ""
        submit = st.form_submit_button("Lưu đơn hàng")
        if submit:
            doc = {
                "MasoDDH": masoddh.strip().upper(),
                "NGAY": ngay.isoformat(),
                "NhaCC": nhacc.strip(),
                "MANV": manv,
                "MAKHO": makho,
            }
            if dathang_col.find_one({"MasoDDH": doc["MasoDDH"]}):
                st.error("Mã đơn đặt hàng đã tồn tại")
            else:
                # Perform the insert within a transaction if the backend supports it
                if client and hasattr(client, "start_session"):
                    session = None
                    try:
                        session = client.start_session()
                        session.start_transaction()
                        dathang_col.insert_one(doc, session=session)
                        # Any related inserts/updates (CTDDH, inventory) would
                        # be added here within the same transaction.
                        session.commit_transaction()
                        st.success("Đã thêm đơn hàng")
                        #st.experimental_rerun()
                        st.rerun()
                    except Exception as e:
                        if session:
                            try:
                                session.abort_transaction()
                            except Exception:
                                pass
                        st.error(f"Lỗi khi thêm đơn hàng: {e}")
                    finally:
                        if session:
                            session.end_session()
                else:
                    try:
                        dathang_col.insert_one(doc)
                        st.success("Đã thêm đơn hàng")
                        #st.experimental_rerun()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi thêm đơn hàng: {e}")


    st.subheader("Chi tiết đơn hàng")
    if orders:
        selected_order = st.selectbox(
            "Chọn đơn hàng để cập nhật chi tiết",
            [o["MasoDDH"] for o in orders],
        )
    else:
        selected_order = None

    if selected_order:
        order_doc = dathang_col.find_one({"MasoDDH": selected_order})
        details = list(ctddh_col.find({"MasoDDH": selected_order}))
        if details:
            df = [
                {
                    "Mã hàng": d.get("MAHANG"),
                    "Số lượng": d.get("SOLUONG"),
                    "Đơn giá": d.get("DONGIA"),
                }
                for d in details
            ]
            st.dataframe(df)
        else:
            st.info("Đơn hàng chưa có chi tiết")

        inventory_col = dbm.get_collection(branch, "Inventory")
        vattu_col = dbm.get_collection(None, "Vattu")
        mahang_opts = [vt["MAHANG"] for vt in vattu_col.find()]

        st.markdown("**Thêm chi tiết**")
        with st.form("ctddh_add_form"):
            mahang = st.selectbox("Mã hàng", mahang_opts)
            soluong = st.number_input("Số lượng", min_value=1, step=1)
            dongia = st.number_input("Đơn giá", min_value=0.0, step=1000.0)
            submit_ct = st.form_submit_button("Lưu chi tiết")
            if submit_ct:
                existing = ctddh_col.find_one({"MasoDDH": selected_order, "MAHANG": mahang})
                if existing:
                    st.error("Mã hàng đã tồn tại trong đơn")
                else:
                    inv = inventory_col.find_one({"MAKHO": order_doc["MAKHO"], "MAHANG": mahang})
                    available = inv.get("SOLUONG", 0) if inv else 0
                    if soluong > available:
                        st.error(f"Tồn kho không đủ (còn {available})")
                    else:
                        ctddh_col.insert_one({
                            "MasoDDH": selected_order,
                            "MAHANG": mahang,
                            "SOLUONG": soluong,
                            "DONGIA": dongia,
                        })
                        inventory_col.update_one(
                            {"MAKHO": order_doc["MAKHO"], "MAHANG": mahang},
                            {"$inc": {"SOLUONG": -soluong}},
                        )
                        st.success("Đã thêm chi tiết")
                        st.rerun()

        if details:
            st.markdown("**Sửa/Xóa chi tiết**")
            edit_mahang = st.selectbox(
                "Chọn chi tiết",
                [d["MAHANG"] for d in details],
                key="ctddh_edit_select",
            )
            edit_doc = next(d for d in details if d["MAHANG"] == edit_mahang)
            with st.form("ctddh_edit_form"):
                new_qty = st.number_input(
                    "Số lượng", min_value=1, value=edit_doc["SOLUONG"], step=1
                )
                new_price = st.number_input(
                    "Đơn giá", min_value=0.0, value=float(edit_doc.get("DONGIA", 0)), step=1000.0
                )
                update_btn = st.form_submit_button("Cập nhật")
                if update_btn:
                    diff = new_qty - edit_doc["SOLUONG"]
                    inv = inventory_col.find_one({"MAKHO": order_doc["MAKHO"], "MAHANG": edit_mahang})
                    available = inv.get("SOLUONG", 0) if inv else 0
                    if diff > 0 and diff > available:
                        st.error(f"Tồn kho không đủ (còn {available})")
                    else:
                        ctddh_col.update_one(
                            {"MasoDDH": selected_order, "MAHANG": edit_mahang},
                            {"$set": {"SOLUONG": new_qty, "DONGIA": new_price}},
                        )
                        if diff != 0:
                            inventory_col.update_one(
                                {"MAKHO": order_doc["MAKHO"], "MAHANG": edit_mahang},
                                {"$inc": {"SOLUONG": -diff}},
                            )
                        st.success("Đã cập nhật")
                        st.rerun()

            if st.button("Xóa chi tiết", key="delete_ctddh"):
                ctddh_col.delete_one({"MasoDDH": selected_order, "MAHANG": edit_mahang})
                inventory_col.update_one(
                    {"MAKHO": order_doc["MAKHO"], "MAHANG": edit_mahang},
                    {"$inc": {"SOLUONG": edit_doc["SOLUONG"]}},
                )
                st.success("Đã xóa chi tiết")
                st.rerun()
    else:
        st.info("Chọn đơn hàng để quản lý chi tiết")


def show_receipts(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """Receipts page for handling PhieuNhap and PhieuXuat."""
    st.header("Phiếu nhập/xuất")
    role = user["role"].capitalize()
    branch = user.get("branch")
    if role == "Congty":
        st.info("Chức năng này hiện chưa hỗ trợ cho quyền Công Ty.")
        return
    # Determine collections and underlying client
    phieunhap_col = dbm.get_collection(branch, "PhieuNhap")
    ctpn_col = dbm.get_collection(branch, "CTPN")
    phieuxuat_col = dbm.get_collection(branch, "PhieuXuat")
    ctpx_col = dbm.get_collection(branch, "CTPX")
    client = None
    if branch == "CN1":
        client = dbm.client_server1
    elif branch == "CN2":
        client = dbm.client_server2

    # Tabs for import/export
    tab1, tab2 = st.tabs(["Phiếu nhập", "Phiếu xuất"])
    with tab1:
        st.subheader("Phiếu nhập hàng")
        pn_list = list(phieunhap_col.find())
        if pn_list:
            df = [
                {
                    "Mã PN": pn.get("MAPN"),
                    "Ngày": pn.get("NGAY"),
                    "Mã đơn": pn.get("MasoDDH"),
                    "Mã NV": pn.get("MANV"),
                    "Mã kho": pn.get("MAKHO"),
                }
                for pn in pn_list
            ]
            st.dataframe(df)
        else:
            st.info("Chưa có phiếu nhập nào")

        st.subheader("Thêm phiếu nhập")
        with st.form("phieunhap_form"):
            mapn = st.text_input("Mã phiếu nhập")
            ngay = st.date_input("Ngày nhập")
            # Must pick an existing order
            dathang_col = dbm.get_collection(branch, "DatHang")
            dh_list = list(dathang_col.find())
            maddh_options = [dh["MasoDDH"] for dh in dh_list]
            masoddh = st.selectbox("Chọn đơn đặt hàng", maddh_options) if maddh_options else ""
            # Employee and warehouse lists
            nhanvien_col = dbm.get_collection(None, "Nhanvien")
            manv_options = [nv["MANV"] for nv in nhanvien_col.find({"MACN": branch})]
            manv = st.selectbox("Nhân viên nhập", manv_options) if manv_options else ""
            kho_col = dbm.get_collection(None, "Kho")
            makho_options = [k["MAKHO"] for k in kho_col.find({"MACN": branch})]
            makho = st.selectbox("Kho", makho_options) if makho_options else ""
            submit_pn = st.form_submit_button("Lưu phiếu nhập")
            if submit_pn:
                doc = {
                    "MAPN": mapn.strip().upper(),
                    "NGAY": ngay.isoformat(),
                    "MasoDDH": masoddh,
                    "MANV": manv,
                    "MAKHO": makho,
                }
                if phieunhap_col.find_one({"MAPN": doc["MAPN"]}):
                    st.error("Mã phiếu nhập đã tồn tại")
                else:
                    if client and hasattr(client, "start_session"):
                        session = None
                        try:
                            session = client.start_session()
                            session.start_transaction()
                            phieunhap_col.insert_one(doc, session=session)
                            # Additional updates like CTPN lines and stock
                            # adjustments would go here within the transaction.
                            session.commit_transaction()
                            st.success("Đã thêm phiếu nhập")
                            #st.experimental_rerun()
                            st.rerun()
                        except Exception as e:
                            if session:
                                try:
                                    session.abort_transaction()
                                except Exception:
                                    pass
                            st.error(f"Lỗi khi thêm phiếu nhập: {e}")
                        finally:
                            if session:
                                session.end_session()
                    else:
                        try:
                            phieunhap_col.insert_one(doc)
                            st.success("Đã thêm phiếu nhập")
                            #st.experimental_rerun()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi thêm phiếu nhập: {e}")

        st.subheader("Chi tiết phiếu nhập")
        selected_pn = st.selectbox(
            "Chọn phiếu nhập", [pn["MAPN"] for pn in pn_list] if pn_list else []
        )
        if selected_pn:
            pn_doc = phieunhap_col.find_one({"MAPN": selected_pn})
            details = list(ctpn_col.find({"MAPN": selected_pn}))
            if details:
                df = [
                    {
                        "Mã hàng": d.get("MAHANG"),
                        "Số lượng": d.get("SOLUONG"),
                        "Đơn giá": d.get("DONGIA"),
                    }
                    for d in details
                ]
                st.dataframe(df)
            else:
                st.info("Chưa có chi tiết")

            inventory_col = dbm.get_collection(branch, "Inventory")
            vattu_col = dbm.get_collection(None, "Vattu")
            mahang_opts = [vt["MAHANG"] for vt in vattu_col.find()]

            st.markdown("**Thêm chi tiết nhập**")
            with st.form("ctpn_add_form"):
                mahang = st.selectbox("Mã hàng", mahang_opts)
                soluong = st.number_input("Số lượng", min_value=1, step=1)
                dongia = st.number_input("Đơn giá", min_value=0.0, step=1000.0)
                submit_ct = st.form_submit_button("Lưu")
                if submit_ct:
                    if ctpn_col.find_one({"MAPN": selected_pn, "MAHANG": mahang}):
                        st.error("Mã hàng đã tồn tại trong phiếu")
                    else:
                        ctpn_col.insert_one(
                            {
                                "MAPN": selected_pn,
                                "MAHANG": mahang,
                                "SOLUONG": soluong,
                                "DONGIA": dongia,
                            }
                        )
                        inventory_col.update_one(
                            {"MAKHO": pn_doc["MAKHO"], "MAHANG": mahang},
                            {"$inc": {"SOLUONG": soluong}},
                            upsert=True,
                        )
                        st.success("Đã thêm chi tiết")
                        st.rerun()

            if details:
                st.markdown("**Sửa/Xóa chi tiết nhập**")
                edit_mahang = st.selectbox(
                    "Chọn chi tiết nhập",
                    [d["MAHANG"] for d in details],
                    key="ctpn_edit_select",
                )
                edit_doc = next(d for d in details if d["MAHANG"] == edit_mahang)
                with st.form("ctpn_edit_form"):
                    new_qty = st.number_input(
                        "Số lượng", min_value=1, value=edit_doc["SOLUONG"], step=1
                    )
                    new_price = st.number_input(
                        "Đơn giá", min_value=0.0, value=float(edit_doc.get("DONGIA", 0)), step=1000.0
                    )
                    submit_edit = st.form_submit_button("Cập nhật")
                    if submit_edit:
                        diff = new_qty - edit_doc["SOLUONG"]
                        ctpn_col.update_one(
                            {"MAPN": selected_pn, "MAHANG": edit_mahang},
                            {"$set": {"SOLUONG": new_qty, "DONGIA": new_price}},
                        )
                        if diff != 0:
                            inventory_col.update_one(
                                {"MAKHO": pn_doc["MAKHO"], "MAHANG": edit_mahang},
                                {"$inc": {"SOLUONG": diff}},
                            )
                        st.success("Đã cập nhật")
                        st.rerun()

                if st.button("Xóa chi tiết nhập", key="delete_ctpn"):
                    ctpn_col.delete_one({"MAPN": selected_pn, "MAHANG": edit_mahang})
                    inventory_col.update_one(
                        {"MAKHO": pn_doc["MAKHO"], "MAHANG": edit_mahang},
                        {"$inc": {"SOLUONG": -edit_doc["SOLUONG"]}},
                    )
                    st.success("Đã xóa chi tiết")
                    st.rerun()

    with tab2:
        st.subheader("Phiếu xuất hàng")
        px_list = list(phieuxuat_col.find())
        if px_list:
            df = [
                {
                    "Mã PX": px.get("MAPX"),
                    "Ngày": px.get("NGAY"),
                    "Họ tên KH": px.get("HOTENKH"),
                    "Mã NV": px.get("MANV"),
                    "Mã kho": px.get("MAKHO"),
                }
                for px in px_list
            ]
            st.dataframe(df)
        else:
            st.info("Chưa có phiếu xuất nào")
        st.subheader("Thêm phiếu xuất")
        with st.form("phieuxuat_form"):
            mapx = st.text_input("Mã phiếu xuất")
            ngay = st.date_input("Ngày xuất")
            hotenkh = st.text_input("Họ tên khách hàng")
            nhanvien_col = dbm.get_collection(None, "Nhanvien")
            manv_options = [nv["MANV"] for nv in nhanvien_col.find({"MACN": branch})]
            manv = st.selectbox("Nhân viên xuất", manv_options) if manv_options else ""
            kho_col = dbm.get_collection(None, "Kho")
            makho_options = [k["MAKHO"] for k in kho_col.find({"MACN": branch})]
            makho = st.selectbox("Kho", makho_options) if makho_options else ""
            submit_px = st.form_submit_button("Lưu phiếu xuất")
            if submit_px:
                doc = {
                    "MAPX": mapx.strip().upper(),
                    "NGAY": ngay.isoformat(),
                    "HOTENKH": hotenkh.strip(),
                    "MANV": manv,
                    "MAKHO": makho,
                }
                if phieuxuat_col.find_one({"MAPX": doc["MAPX"]}):
                    st.error("Mã phiếu xuất đã tồn tại")
                else:
                    if client and hasattr(client, "start_session"):
                        session = None
                        try:
                            session = client.start_session()
                            session.start_transaction()
                            phieuxuat_col.insert_one(doc, session=session)
                            # Related updates like CTPX lines and stock adjustments
                            # would also execute here within the transaction.
                            session.commit_transaction()
                            st.success("Đã thêm phiếu xuất")
                            #st.experimental_rerun()
                            st.rerun()
                        except Exception as e:
                            if session:
                                try:
                                    session.abort_transaction()
                                except Exception:
                                    pass
                            st.error(f"Lỗi khi thêm phiếu xuất: {e}")
                        finally:
                            if session:
                                session.end_session()
                    else:
                        try:
                            phieuxuat_col.insert_one(doc)
                            st.success("Đã thêm phiếu xuất")
                            #st.experimental_rerun()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi thêm phiếu xuất: {e}")

        st.subheader("Chi tiết phiếu xuất")
        selected_px = st.selectbox(
            "Chọn phiếu xuất", [px["MAPX"] for px in px_list] if px_list else []
        )
        if selected_px:
            px_doc = phieuxuat_col.find_one({"MAPX": selected_px})
            details = list(ctpx_col.find({"MAPX": selected_px}))
            if details:
                df = [
                    {
                        "Mã hàng": d.get("MAHANG"),
                        "Số lượng": d.get("SOLUONG"),
                        "Đơn giá": d.get("DONGIA"),
                    }
                    for d in details
                ]
                st.dataframe(df)
            else:
                st.info("Chưa có chi tiết")

            inventory_col = dbm.get_collection(branch, "Inventory")
            vattu_col = dbm.get_collection(None, "Vattu")
            mahang_opts = [vt["MAHANG"] for vt in vattu_col.find()]

            st.markdown("**Thêm chi tiết xuất**")
            with st.form("ctpx_add_form"):
                mahang = st.selectbox("Mã hàng", mahang_opts)
                soluong = st.number_input("Số lượng", min_value=1, step=1)
                dongia = st.number_input("Đơn giá", min_value=0.0, step=1000.0)
                submit_ct = st.form_submit_button("Lưu")
                if submit_ct:
                    if ctpx_col.find_one({"MAPX": selected_px, "MAHANG": mahang}):
                        st.error("Mã hàng đã tồn tại trong phiếu")
                    else:
                        inv = inventory_col.find_one({"MAKHO": px_doc["MAKHO"], "MAHANG": mahang})
                        available = inv.get("SOLUONG", 0) if inv else 0
                        if soluong > available:
                            st.error(f"Tồn kho không đủ (còn {available})")
                        else:
                            ctpx_col.insert_one(
                                {
                                    "MAPX": selected_px,
                                    "MAHANG": mahang,
                                    "SOLUONG": soluong,
                                    "DONGIA": dongia,
                                }
                            )
                            inventory_col.update_one(
                                {"MAKHO": px_doc["MAKHO"], "MAHANG": mahang},
                                {"$inc": {"SOLUONG": -soluong}},
                            )
                            st.success("Đã thêm chi tiết")
                            st.rerun()

            if details:
                st.markdown("**Sửa/Xóa chi tiết xuất**")
                edit_mahang = st.selectbox(
                    "Chọn chi tiết xuất",
                    [d["MAHANG"] for d in details],
                    key="ctpx_edit_select",
                )
                edit_doc = next(d for d in details if d["MAHANG"] == edit_mahang)
                with st.form("ctpx_edit_form"):
                    new_qty = st.number_input(
                        "Số lượng", min_value=1, value=edit_doc["SOLUONG"], step=1
                    )
                    new_price = st.number_input(
                        "Đơn giá", min_value=0.0, value=float(edit_doc.get("DONGIA", 0)), step=1000.0
                    )
                    submit_edit = st.form_submit_button("Cập nhật")
                    if submit_edit:
                        diff = new_qty - edit_doc["SOLUONG"]
                        inv = inventory_col.find_one({"MAKHO": px_doc["MAKHO"], "MAHANG": edit_mahang})
                        available = inv.get("SOLUONG", 0) if inv else 0
                        if diff > 0 and diff > available:
                            st.error(f"Tồn kho không đủ (còn {available})")
                        else:
                            ctpx_col.update_one(
                                {"MAPX": selected_px, "MAHANG": edit_mahang},
                                {"$set": {"SOLUONG": new_qty, "DONGIA": new_price}},
                            )
                            if diff != 0:
                                inventory_col.update_one(
                                    {"MAKHO": px_doc["MAKHO"], "MAHANG": edit_mahang},
                                    {"$inc": {"SOLUONG": -diff}},
                                )
                            st.success("Đã cập nhật")
                            st.rerun()

                if st.button("Xóa chi tiết xuất", key="delete_ctpx"):
                    ctpx_col.delete_one({"MAPX": selected_px, "MAHANG": edit_mahang})
                    inventory_col.update_one(
                        {"MAKHO": px_doc["MAKHO"], "MAHANG": edit_mahang},
                        {"$inc": {"SOLUONG": edit_doc["SOLUONG"]}},
                    )
                    st.success("Đã xóa chi tiết")
                    st.rerun()


def show_create_account(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """UI for creating new login accounts."""
    st.header("Tạo tài khoản mới")
    role = user["role"].capitalize()
    if role not in {"Congty", "Chinhanh"}:
        st.warning("Bạn không có quyền tạo tài khoản mới")
        return
    with st.form("create_account_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        # Role selection based on current user
        if role == "Congty":
            role_options = ["CongTy", "ChiNhanh", "User"]
        else:
            # ChiNhanh can only create ChiNhanh or User
            role_options = ["ChiNhanh", "User"]
        selected_role = st.selectbox("Nhóm quyền", role_options)
        branch = None
        if selected_role in {"ChiNhanh", "User"}:
            # Branch must be chosen
            if role == "Congty":
                branch = st.selectbox("Chi nhánh", ["CN1", "CN2"])
            else:
                branch = user.get("branch")
                st.info(f"Tài khoản sẽ được gán cho chi nhánh {branch}")
        submit = st.form_submit_button("Tạo tài khoản")
        if submit:
            try:
                auth.create_user(dbm, username, password, selected_role, branch)
                st.success("Đã tạo tài khoản thành công")
            except Exception as e:
                st.error(str(e))


def show_reports(dbm: DatabaseManager, user: Dict[str, Any]) -> None:
    """Placeholder for reports accessible to CongTy."""
    st.header("Báo cáo")
    st.info(
        "Chức năng báo cáo có thể bao gồm tổng hợp doanh thu, tồn kho, "
        "số lượng đơn hàng theo chi nhánh… Bạn có thể sử dụng Pandas và các "
        "biểu đồ trong Streamlit để xây dựng trang báo cáo trong tương lai."
    )


if __name__ == "__main__":
    main()
