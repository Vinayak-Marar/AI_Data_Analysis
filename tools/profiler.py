import pandas as pd
import datetime


def profile_dataframe(df: pd.DataFrame) -> str:
    """Return rich metadata profile for planner context."""
    lines = []

    # Basic shape
    lines.append(f"ROWS: {df.shape[0]}")
    lines.append(f"COLUMNS: {df.shape[1]}")
    lines.append(f"MEMORY USAGE: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")

    # Column listing
    lines.append("\nALL COLUMN NAMES:")
    for col in df.columns:
        lines.append(f"  - {col}")

    # Classify columns
    numeric_cols = list(df.select_dtypes(include="number").columns)
    categorical_cols = list(df.select_dtypes(include=["object", "category"]).columns)
    datetime_cols = list(df.select_dtypes(include=["datetime64"]).columns)

    # Also detect time columns stored as object
    time_cols = []
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, datetime.time)).any():
            time_cols.append(col)

    lines.append(f"\nNUMERIC COLUMNS ({len(numeric_cols)}): {numeric_cols}")
    lines.append(f"CATEGORICAL COLUMNS ({len(categorical_cols)}): {categorical_cols}")
    lines.append(f"DATETIME COLUMNS ({len(datetime_cols)}): {datetime_cols}")
    if time_cols:
        lines.append(f"TIME COLUMNS ({len(time_cols)}): {time_cols}")

    # Missing values
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0]
    lines.append(f"\nDUPLICATE ROWS: {df.duplicated().sum()}")
    if missing_cols.empty:
        lines.append("MISSING VALUES: None")
    else:
        lines.append("MISSING VALUES:")
        for col, count in missing_cols.items():
            pct = count / len(df) * 100
            lines.append(f"  - {col}: {count} ({pct:.1f}%)")

    # Numeric stats
    if numeric_cols:
        lines.append("\nNUMERIC STATISTICS:")
        desc = df[numeric_cols].describe().round(2)
        lines.append(desc.to_string())

    # Categorical stats
    if categorical_cols:
        lines.append("\nCATEGORICAL COLUMNS — UNIQUE COUNTS AND TOP VALUES:")
        for col in categorical_cols[:10]:
            n_unique = df[col].nunique()
            top = df[col].value_counts().head(5).to_dict()
            lines.append(f"  {col}: {n_unique} unique | top: {top}")

    # Sample rows
    lines.append(f"\nSAMPLE (first 3 rows):")
    lines.append(df.head(3).to_string())

    return "\n".join(lines)