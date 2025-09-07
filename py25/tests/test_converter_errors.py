import json
from pathlib import Path
import pytest
from toolkit_cli import Converter

def test_json_to_csv_erro_quando_nao_lista(tmp_path: Path):
    j = tmp_path / "bad.json"
    j.write_text(json.dumps({"a": 1}), encoding="utf-8")  # não é lista
    with pytest.raises(ValueError):
        Converter.json_to_csv(j, tmp_path / "out.csv")
