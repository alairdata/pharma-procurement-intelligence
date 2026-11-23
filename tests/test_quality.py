import pandas as pd

from src.pipeline.quality import DataQualityError, validate


def sample_df():
    return pd.DataFrame({
        "source": ["x", "x"],
        "source_record_id": ["1", "2"],
        "country": ["Ghana", "Kenya"],
        "supplier_entity": ["Supplier A", "Supplier B"],
        "product_key": ["drug-a", "drug-b"],
        "pack_price_usd": [3.5, 4.0],
        "quantity": [10, 20],
    })


def test_quality_passes_valid_rows(tmp_path, monkeypatch):
    df = sample_df()
    result = validate(df)
    assert result["passed"] is True


def test_quality_rejects_negative_price():
    df = sample_df()
    df.loc[0, "pack_price_usd"] = -1
    try:
        validate(df)
        assert False, "Expected DataQualityError"
    except DataQualityError:
        assert True
