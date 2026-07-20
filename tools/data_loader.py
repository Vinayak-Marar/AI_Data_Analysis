import pandas as pd

def load_dataframe(filepath: str) -> pd.DataFrame:
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    elif filepath.endswith((".xlsx", ".xls")):
        return pd.read_excel(filepath)
    raise ValueError("Unsupported file type")