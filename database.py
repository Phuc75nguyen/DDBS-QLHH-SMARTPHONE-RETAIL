"""
Database abstraction layer for the distributed inventory management system.

This module centralizes all logic for connecting to the underlying MongoDB
instances and provides convenience functions for accessing the appropriate
collections depending on the branch. The requirement for this project is to
split the database into three fragments:

* server1 – contains all order and receipt documents for branch 1 (CN1).
* server2 – contains all order and receipt documents for branch 2 (CN2).
* server3 – holds shared reference data such as employee and warehouse lists for
  both branches. A `users` collection also resides here to support the
  authentication layer.

In a real‑world deployment these would be three separate MongoDB servers or
clusters. For ease of development and testing the module will fall back to
`mongomock`, a pure Python in‑memory mock of MongoDB, if a real MongoDB
instance is not available. When deploying against production, ensure that
`MONGODB_URI_SERVER1`, `MONGODB_URI_SERVER2` and `MONGODB_URI_SERVER3` are
provided in the environment and point at your running `mongod` processes.

References:
The PyMongo tutorial demonstrates how to establish a connection using
`MongoClient` and explains that you can specify the host and port
explicitly. For example, `client = MongoClient("localhost", 27017)`
creates a connection to a local MongoDB instance【282328984375463†L168-L193】.

"""

import os
from typing import Dict, Any, Optional

try:
    # Try to import the official PyMongo driver.  If it’s not available
    # (for example in a constrained environment), we'll fall back to mongomock.
    from pymongo import MongoClient  # type: ignore
    from pymongo.collection import Collection  # type: ignore
    pymongo_available = True
except ImportError:  # pragma: no cover - fallback when PyMongo is missing
    pymongo_available = False
    MongoClient = None  # type: ignore
    Collection = None  # type: ignore

try:
    import mongomock  # type: ignore
    mongomock_available = True
except ImportError:  # pragma: no cover - mongomock is optional
    mongomock_available = False


class DatabaseManager:
    """Central manager to handle connections to distributed MongoDB servers.

    Each branch uses a different server for transactional data, while shared
    reference data lives on a separate server. Connection URIs can be
    configured via environment variables or passed directly when instantiating
    this class.  When no URI is supplied, an in‑memory MongoDB instance is
    constructed using mongomock to facilitate local development and unit
    testing.
    """

    def __init__(
        self,
        uri_server1: Optional[str] = None,
        uri_server2: Optional[str] = None,
        uri_server3: Optional[str] = None,
    ) -> None:
        # Determine connection strings: environment variables take precedence
        self.uri_server1 = uri_server1 or os.getenv("MONGODB_URI_SERVER1")
        self.uri_server2 = uri_server2 or os.getenv("MONGODB_URI_SERVER2")
        self.uri_server3 = uri_server3 or os.getenv("MONGODB_URI_SERVER3")

        # Initialize clients for each server
        self.client_server1 = self._create_client(self.uri_server1, name="server1")
        self.client_server2 = self._create_client(self.uri_server2, name="server2")
        self.client_server3 = self._create_client(self.uri_server3, name="server3")

        # Databases on each server; using the same name for clarity
        self.db_server1 = self.client_server1["qlhh_server1"]
        self.db_server2 = self.client_server2["qlhh_server2"]
        self.db_server3 = self.client_server3["qlhh_server3"]

    def _create_client(self, uri: Optional[str], name: str):
        """Create a MongoDB client for a server.

        Attempts to connect using PyMongo if available. If PyMongo isn't
        installed or a URI isn't provided, falls back to a mongomock client.

        Args:
            uri: Connection string for MongoDB; may include username and
                password. If `None`, a mongomock client is used.
            name: Human friendly name of the server used for logging.

        Returns:
            A MongoClient‑like instance.
        """
        if uri and pymongo_available:
            # Use a real MongoDB connection
            return MongoClient(uri)
        # Fallback: use mongomock for in‑memory database
        if not mongomock_available:
            raise RuntimeError(
                f"Neither PyMongo nor mongomock is available. You must install at least one"
            )
        return mongomock.MongoClient()

    def get_collection(self, branch: str, collection_name: str) -> Any:
        """Return the appropriate collection for a given branch.

        Transactional collections (such as orders and receipts) reside on
        server1 if the branch is `CN1` and on server2 if the branch is `CN2`.
        Shared collections (employee, warehouse, users) live on server3.

        Args:
            branch: Branch code (e.g., "CN1" or "CN2"). When `None`, the
                collection is assumed to be shared and thus read from server3.
            collection_name: Name of the MongoDB collection.

        Returns:
            The requested collection object.
        """
        branch = branch.upper() if branch else None
        # Determine which server holds the collection
        transactional_collections = {
            "DatHang",
            "CTDDH",
            "PhieuNhap",
            "CTPN",
            "PhieuXuat",
            "CTPX",
            "Inventory",
        }
        reference_collections = {
            "Nhanvien",
            "Kho",
            "Vattu",
            "users",
        }

        if collection_name in reference_collections:
            # Shared collections live on server3
            return self.db_server3[collection_name]
        if collection_name in transactional_collections:
            if branch == "CN1":
                return self.db_server1[collection_name]
            elif branch == "CN2":
                return self.db_server2[collection_name]
            else:
                raise ValueError(f"Unsupported branch for transactional data: {branch}")
        # For undefined collections assume server3
        return self.db_server3[collection_name]

    def init_schema(self) -> None:
        """Ensure indexes and basic fields exist for all collections.

        MongoDB creates collections lazily when inserting the first document.
        This method explicitly creates unique indexes for primary keys where
        applicable. If the index already exists, MongoDB ignores the call.

        We create indexes on the following fields to enforce uniqueness:

          * `ChiNhanh.MACN`
          * `Nhanvien.MANV`
          * `Kho.MAKHO`
          * `Vattu.MAHANG`
          * `DatHang.MasoDDH`
          * `PhieuNhap.MAPN`
          * `PhieuXuat.MAPX`
          * `users.username`

        The unique indexes ensure there are no duplicate primary keys within a
        collection.
        """
        # Ensure indexes on reference collections
        self.db_server3["Nhanvien"].create_index("MANV", unique=True)
        self.db_server3["Kho"].create_index("MAKHO", unique=True)
        self.db_server3["Vattu"].create_index("MAHANG", unique=True)
        self.db_server3["users"].create_index("username", unique=True)

        
        # Primary documents have single-field unique indexes
        for col_name, key in [
            ("DatHang", "MasoDDH"),
            ("PhieuNhap", "MAPN"),
            ("PhieuXuat", "MAPX"),
        ]:
            self.db_server1[col_name].create_index(key, unique=True, sparse=True)
            self.db_server2[col_name].create_index(key, unique=True, sparse=True)

        # Detail lines use compound indexes to avoid duplicates
        for col_name, keys in [
            ("CTDDH", [("MasoDDH", 1), ("MAHANG", 1)]),
            ("CTPN", [("MAPN", 1), ("MAHANG", 1)]),
            ("CTPX", [("MAPX", 1), ("MAHANG", 1)]),
            ("Inventory", [("MAKHO", 1), ("MAHANG", 1)]),
        ]:
            self.db_server1[col_name].create_index(keys, unique=True)
            self.db_server2[col_name].create_index(keys, unique=True)

    def seed_demo_data(self) -> None:
        """Populate the database with a small set of sample records.

        This helper inserts a couple of branches, employees, warehouses and
        materials to allow the Streamlit application to run without requiring
        manual data entry. In production this method should not be called or
        should be adapted to your own dataset.
        """
        # Sample employees – all stored on server3
        nhanvien = self.db_server3["Nhanvien"]
        if nhanvien.count_documents({}) == 0:
            nhanvien.insert_many([
                {
                    "MANV": "NV01",
                    "HO": "Nguyen",
                    "TEN": "Van A",
                    "DIACHI": "Hanoi",
                    "NGAYSINH": "1990-01-01",
                    "LUONG": 1000,
                    "MACN": "CN1",
                },
                {
                    "MANV": "NV02",
                    "HO": "Le",
                    "TEN": "Thi B",
                    "DIACHI": "Saigon",
                    "NGAYSINH": "1992-05-15",
                    "LUONG": 1200,
                    "MACN": "CN2",
                },
            ])

        # Sample warehouses
        kho = self.db_server3["Kho"]
        if kho.count_documents({}) == 0:
            kho.insert_many([
                {
                    "MAKHO": "KHO1",
                    "TENKHO": "Kho CN1",
                    "DIACHI": "Hanoi",
                    "MACN": "CN1",
                },
                {
                    "MAKHO": "KHO2",
                    "TENKHO": "Kho CN2",
                    "DIACHI": "Saigon",
                    "MACN": "CN2",
                },
            ])

        # Sample materials
        vattu = self.db_server3["Vattu"]
        if vattu.count_documents({}) == 0:
            vattu.insert_many([
                {"MAHANG": "VT01", "TENHANG": "iPhone 15", "DVT": " chiếc"},
                {"MAHANG": "VT02", "TENHANG": "Samsung S23", "DVT": " chiếc"},
                {"MAHANG": "VT03", "TENHANG": "Oppo Reno10", "DVT": " chiếc"},
            ])

        # Initial inventory for each branch warehouse
        inv1 = self.db_server1["Inventory"]
        inv2 = self.db_server2["Inventory"]
        if inv1.count_documents({}) == 0:
            inv1.insert_many([
                {"MAKHO": "KHO1", "MAHANG": "VT01", "SOLUONG": 100},
                {"MAKHO": "KHO1", "MAHANG": "VT02", "SOLUONG": 100},
                {"MAKHO": "KHO1", "MAHANG": "VT03", "SOLUONG": 100},
            ])
        if inv2.count_documents({}) == 0:
            inv2.insert_many([
                {"MAKHO": "KHO2", "MAHANG": "VT01", "SOLUONG": 100},
                {"MAKHO": "KHO2", "MAHANG": "VT02", "SOLUONG": 100},
                {"MAKHO": "KHO2", "MAHANG": "VT03", "SOLUONG": 100},
            ])
