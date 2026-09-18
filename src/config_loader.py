# -*- coding: utf-8 -*-
"""
統一的 config/*.yaml 讀取入口。

安全設計：任何載入失敗（檔案不存在、YAML格式錯誤、資料不符合預期結構）一律直接丟例外讓
程式啟動失敗，不能悄悄退回某種預設權限表——權限分級表這種安全關鍵資料，寧可讓程式開不起來，
也不能在資料有問題時還假裝一切正常運作（那樣可能導致某個原本該L3確認的危險工具，因為YAML
打錯字讀不到，默默變成沒有任何限制）。
"""
import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def load_yaml(filename: str) -> dict:
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"設定檔不存在：{path}（這是安全關鍵資料，不能省略或跳過）")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"設定檔格式不對，最外層應該是一個對照表(dict)：{path}")
    return data


def load_permissions() -> dict:
    return load_yaml("permissions.yaml")


def load_tools_config() -> dict:
    return load_yaml("tools.yaml")


def load_runtime_config() -> dict:
    """
    runtime.yaml：語音/LLM管線的可調參數（喚醒詞門檻、端點偵測靜音長度、緊急停止熱鍵等）。
    跟permissions.yaml不同——這些不是安全關鍵資料，讀取失敗不會導致系統變得不安全，但仍然
    直接丟例外而不是悄悄退回硬編碼預設值，理由跟其餘config一致：設定檔打錯字應該讓人立刻
    發現，不是默默套用一個使用者不知道的預設行為。
    """
    return load_yaml("runtime.yaml")
