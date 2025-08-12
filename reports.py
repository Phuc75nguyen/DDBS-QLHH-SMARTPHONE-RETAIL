import pandas as pd
from database import DatabaseManager


def _get_branches(dbm: DatabaseManager) -> list:
    """Return a list of branch codes present in the system."""
    kho_col = dbm.get_collection(None, "Kho")
    df = pd.DataFrame(list(kho_col.find()))
    if df.empty:
        return []
    return df["MACN"].dropna().unique().tolist()


def revenue_by_branch(dbm: DatabaseManager) -> pd.DataFrame:
    """Aggregate revenue (as count of export receipts) per branch."""
    branches = _get_branches(dbm)
    records = []
    for branch in branches:
        px_col = dbm.get_collection(branch, "PhieuXuat")
        px_df = pd.DataFrame(list(px_col.find()))
        revenue = len(px_df)
        records.append({"branch": branch, "revenue": revenue})
    return pd.DataFrame(records)


def inventory_by_branch(dbm: DatabaseManager) -> pd.DataFrame:
    """Compute a simple inventory metric based on imports minus exports."""
    branches = _get_branches(dbm)
    records = []
    for branch in branches:
        pn_df = pd.DataFrame(list(dbm.get_collection(branch, "PhieuNhap").find()))
        px_df = pd.DataFrame(list(dbm.get_collection(branch, "PhieuXuat").find()))
        inventory = len(pn_df) - len(px_df)
        records.append({"branch": branch, "inventory": inventory})
    return pd.DataFrame(records)
