import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
from database import DatabaseManager
try:
    from pymongo.errors import DuplicateKeyError
except Exception:
    try:
        from mongomock import DuplicateKeyError
    except Exception:
        DuplicateKeyError = Exception


def add_order_detail(dbm, branch, order_id, makho, mahang, qty, price):
    ct_col = dbm.get_collection(branch, "CTDDH")
    inv_col = dbm.get_collection(branch, "Inventory")
    if ct_col.find_one({"MasoDDH": order_id, "MAHANG": mahang}):
        raise ValueError("duplicate detail")
    inv = inv_col.find_one({"MAKHO": makho, "MAHANG": mahang})
    available = inv.get("SOLUONG", 0) if inv else 0
    if qty > available:
        raise ValueError("insufficient stock")
    ct_col.insert_one({
        "MasoDDH": order_id,
        "MAHANG": mahang,
        "SOLUONG": qty,
        "DONGIA": price,
    })
    inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": -qty}})


def edit_order_detail(dbm, branch, order_id, makho, mahang, new_qty, new_price):
    ct_col = dbm.get_collection(branch, "CTDDH")
    inv_col = dbm.get_collection(branch, "Inventory")
    detail = ct_col.find_one({"MasoDDH": order_id, "MAHANG": mahang})
    diff = new_qty - detail["SOLUONG"]
    inv = inv_col.find_one({"MAKHO": makho, "MAHANG": mahang})
    available = inv.get("SOLUONG", 0) if inv else 0
    if diff > 0 and diff > available:
        raise ValueError("insufficient stock")
    ct_col.update_one(
        {"MasoDDH": order_id, "MAHANG": mahang},
        {"$set": {"SOLUONG": new_qty, "DONGIA": new_price}},
    )
    if diff != 0:
        inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": -diff}})


def delete_order_detail(dbm, branch, order_id, makho, mahang):
    ct_col = dbm.get_collection(branch, "CTDDH")
    inv_col = dbm.get_collection(branch, "Inventory")
    detail = ct_col.find_one({"MasoDDH": order_id, "MAHANG": mahang})
    ct_col.delete_one({"MasoDDH": order_id, "MAHANG": mahang})
    inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": detail["SOLUONG"]}})


def add_export_detail(dbm, branch, px_id, makho, mahang, qty, price):
    ct_col = dbm.get_collection(branch, "CTPX")
    inv_col = dbm.get_collection(branch, "Inventory")
    if ct_col.find_one({"MAPX": px_id, "MAHANG": mahang}):
        raise ValueError("duplicate detail")
    inv = inv_col.find_one({"MAKHO": makho, "MAHANG": mahang})
    available = inv.get("SOLUONG", 0) if inv else 0
    if qty > available:
        raise ValueError("insufficient stock")
    ct_col.insert_one({
        "MAPX": px_id,
        "MAHANG": mahang,
        "SOLUONG": qty,
        "DONGIA": price,
    })
    inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": -qty}})


def edit_export_detail(dbm, branch, px_id, makho, mahang, new_qty, new_price):
    ct_col = dbm.get_collection(branch, "CTPX")
    inv_col = dbm.get_collection(branch, "Inventory")
    detail = ct_col.find_one({"MAPX": px_id, "MAHANG": mahang})
    diff = new_qty - detail["SOLUONG"]
    inv = inv_col.find_one({"MAKHO": makho, "MAHANG": mahang})
    available = inv.get("SOLUONG", 0) if inv else 0
    if diff > 0 and diff > available:
        raise ValueError("insufficient stock")
    ct_col.update_one(
        {"MAPX": px_id, "MAHANG": mahang},
        {"$set": {"SOLUONG": new_qty, "DONGIA": new_price}},
    )
    if diff != 0:
        inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": -diff}})


def delete_export_detail(dbm, branch, px_id, makho, mahang):
    ct_col = dbm.get_collection(branch, "CTPX")
    inv_col = dbm.get_collection(branch, "Inventory")
    detail = ct_col.find_one({"MAPX": px_id, "MAHANG": mahang})
    ct_col.delete_one({"MAPX": px_id, "MAHANG": mahang})
    inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": detail["SOLUONG"]}})


def add_import_detail(dbm, branch, pn_id, makho, mahang, qty, price):
    ct_col = dbm.get_collection(branch, "CTPN")
    inv_col = dbm.get_collection(branch, "Inventory")
    if ct_col.find_one({"MAPN": pn_id, "MAHANG": mahang}):
        raise ValueError("duplicate detail")
    ct_col.insert_one({"MAPN": pn_id, "MAHANG": mahang, "SOLUONG": qty, "DONGIA": price})
    inv_col.update_one(
        {"MAKHO": makho, "MAHANG": mahang},
        {"$inc": {"SOLUONG": qty}},
        upsert=True,
    )


def edit_import_detail(dbm, branch, pn_id, makho, mahang, new_qty, new_price):
    ct_col = dbm.get_collection(branch, "CTPN")
    inv_col = dbm.get_collection(branch, "Inventory")
    detail = ct_col.find_one({"MAPN": pn_id, "MAHANG": mahang})
    diff = new_qty - detail["SOLUONG"]
    ct_col.update_one(
        {"MAPN": pn_id, "MAHANG": mahang},
        {"$set": {"SOLUONG": new_qty, "DONGIA": new_price}},
    )
    if diff != 0:
        inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": diff}})


def delete_import_detail(dbm, branch, pn_id, makho, mahang):
    ct_col = dbm.get_collection(branch, "CTPN")
    inv_col = dbm.get_collection(branch, "Inventory")
    detail = ct_col.find_one({"MAPN": pn_id, "MAHANG": mahang})
    ct_col.delete_one({"MAPN": pn_id, "MAHANG": mahang})
    inv_col.update_one({"MAKHO": makho, "MAHANG": mahang}, {"$inc": {"SOLUONG": -detail["SOLUONG"]}})


@pytest.fixture
def dbm():
    dbm = DatabaseManager()
    dbm.init_schema()
    dbm.seed_demo_data()
    return dbm


def _prepare_order(dbm):
    branch = "CN1"
    makho = "KHO1"
    dathang = dbm.get_collection(branch, "DatHang")
    dathang.insert_one({
        "MasoDDH": "DH001",
        "NGAY": "2023-01-01",
        "NhaCC": "NCC",
        "MANV": "NV01",
        "MAKHO": makho,
    })
    return branch, makho


def _prepare_export(dbm):
    branch = "CN1"
    makho = "KHO1"
    phieuxuat = dbm.get_collection(branch, "PhieuXuat")
    phieuxuat.insert_one({
        "MAPX": "PX001",
        "NGAY": "2023-01-01",
        "HOTENKH": "A",
        "MANV": "NV01",
        "MAKHO": makho,
    })
    return branch, makho


def _prepare_import(dbm):
    branch = "CN1"
    makho = "KHO1"
    phieunhap = dbm.get_collection(branch, "PhieuNhap")
    phieunhap.insert_one({
        "MAPN": "PN001",
        "NGAY": "2023-01-01",
        "MasoDDH": "DHX",
        "MANV": "NV01",
        "MAKHO": makho,
    })
    return branch, makho


def test_add_order_detail_insufficient_stock(dbm):
    branch, makho = _prepare_order(dbm)
    inv_col = dbm.get_collection(branch, "Inventory")
    available = inv_col.find_one({"MAKHO": makho, "MAHANG": "VT01"})["SOLUONG"]
    with pytest.raises(ValueError):
        add_order_detail(dbm, branch, "DH001", makho, "VT01", available + 1, 1000)
    assert dbm.get_collection(branch, "CTDDH").count_documents({}) == 0
    assert (
        inv_col.find_one({"MAKHO": makho, "MAHANG": "VT01"})["SOLUONG"]
        == available
    )


def test_edit_order_detail_insufficient_stock(dbm):
    branch, makho = _prepare_order(dbm)
    add_order_detail(dbm, branch, "DH001", makho, "VT01", 10, 1000)
    inv_col = dbm.get_collection(branch, "Inventory")
    with pytest.raises(ValueError):
        edit_order_detail(dbm, branch, "DH001", makho, "VT01", 200, 1000)
    detail = dbm.get_collection(branch, "CTDDH").find_one({"MasoDDH": "DH001", "MAHANG": "VT01"})
    assert detail["SOLUONG"] == 10
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT01"})["SOLUONG"] == 90


def test_add_export_detail_insufficient_stock(dbm):
    branch, makho = _prepare_export(dbm)
    inv_col = dbm.get_collection(branch, "Inventory")
    available = inv_col.find_one({"MAKHO": makho, "MAHANG": "VT01"})["SOLUONG"]
    with pytest.raises(ValueError):
        add_export_detail(dbm, branch, "PX001", makho, "VT01", available + 5, 1000)
    assert dbm.get_collection(branch, "CTPX").count_documents({}) == 0
    assert (
        inv_col.find_one({"MAKHO": makho, "MAHANG": "VT01"})["SOLUONG"]
        == available
    )


def test_edit_export_detail_insufficient_stock(dbm):
    branch, makho = _prepare_export(dbm)
    add_export_detail(dbm, branch, "PX001", makho, "VT01", 10, 1000)
    inv_col = dbm.get_collection(branch, "Inventory")
    with pytest.raises(ValueError):
        edit_export_detail(dbm, branch, "PX001", makho, "VT01", 200, 1000)
    detail = dbm.get_collection(branch, "CTPX").find_one({"MAPX": "PX001", "MAHANG": "VT01"})
    assert detail["SOLUONG"] == 10
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT01"})["SOLUONG"] == 90


def test_duplicate_detail_line_prevention(dbm):
    branch, makho = _prepare_order(dbm)
    ctddh = dbm.get_collection(branch, "CTDDH")
    ctddh.insert_one({"MasoDDH": "DH001", "MAHANG": "VT02", "SOLUONG": 5, "DONGIA": 1})
    with pytest.raises(DuplicateKeyError):
        ctddh.insert_one({"MasoDDH": "DH001", "MAHANG": "VT02", "SOLUONG": 1, "DONGIA": 1})

    branch, makho = _prepare_import(dbm)
    ctpn = dbm.get_collection(branch, "CTPN")
    ctpn.insert_one({"MAPN": "PN001", "MAHANG": "VT02", "SOLUONG": 5, "DONGIA": 1})
    with pytest.raises(DuplicateKeyError):
        ctpn.insert_one({"MAPN": "PN001", "MAHANG": "VT02", "SOLUONG": 1, "DONGIA": 1})

    branch, makho = _prepare_export(dbm)
    ctpx = dbm.get_collection(branch, "CTPX")
    ctpx.insert_one({"MAPX": "PX001", "MAHANG": "VT02", "SOLUONG": 5, "DONGIA": 1})
    with pytest.raises(DuplicateKeyError):
        ctpx.insert_one({"MAPX": "PX001", "MAHANG": "VT02", "SOLUONG": 1, "DONGIA": 1})


def test_inventory_rollback_on_edit_delete(dbm):
    branch, makho = _prepare_order(dbm)
    add_order_detail(dbm, branch, "DH001", makho, "VT03", 10, 1)
    inv_col = dbm.get_collection(branch, "Inventory")
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 90
    edit_order_detail(dbm, branch, "DH001", makho, "VT03", 5, 1)
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 95
    delete_order_detail(dbm, branch, "DH001", makho, "VT03")
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 100

    branch, makho = _prepare_import(dbm)
    add_import_detail(dbm, branch, "PN001", makho, "VT03", 20, 1)
    inv_col = dbm.get_collection(branch, "Inventory")
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 120
    edit_import_detail(dbm, branch, "PN001", makho, "VT03", 30, 1)
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 130
    delete_import_detail(dbm, branch, "PN001", makho, "VT03")
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 100

    branch, makho = _prepare_export(dbm)
    add_export_detail(dbm, branch, "PX001", makho, "VT03", 10, 1)
    inv_col = dbm.get_collection(branch, "Inventory")
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 90
    edit_export_detail(dbm, branch, "PX001", makho, "VT03", 5, 1)
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 95
    delete_export_detail(dbm, branch, "PX001", makho, "VT03")
    assert inv_col.find_one({"MAKHO": makho, "MAHANG": "VT03"})["SOLUONG"] == 100
