import os
import pandas as pd
import streamlit as st

from modules.constants import PART_TO_DAY
from modules.youtube_utils import build_youtube_urls

TRAININGS_DIR = "assets/trainings_list"
TRAININGS_CSV_PATH = os.path.join(TRAININGS_DIR, "trainings_list.csv")
TRAININGS_XLSX_PATH = os.path.join(TRAININGS_DIR, "trainings_list.xlsx")

@st.cache_data(show_spinner=False)
def load_training_list() -> pd.DataFrame:
    # どちらも無ければ空
    if not os.path.exists(TRAININGS_CSV_PATH) and not os.path.exists(TRAININGS_XLSX_PATH):
        return pd.DataFrame(
            columns=["種目名", "部位", "動画LINK", "動画開始時間(sec)", "必須/選択",
                     "DAY", "is_required", "video_embed_url", "video_watch_url"]
        )

    if os.path.exists(TRAININGS_CSV_PATH):
        try:
            df = pd.read_csv(TRAININGS_CSV_PATH, encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(TRAININGS_CSV_PATH, encoding="utf-8")
    else:
        df = pd.read_excel(TRAININGS_XLSX_PATH)

    for col in ["種目名", "部位", "動画LINK", "動画開始時間(sec)", "必須/選択"]:
        if col not in df.columns:
            df[col] = ""

    df = df.dropna(subset=["種目名"]).copy()
    df["種目名"] = df["種目名"].astype(str).str.strip()
    df["部位"] = df["部位"].astype(str).str.strip()
    df["動画LINK"] = df["動画LINK"].astype(str).str.strip()
    df["必須/選択"] = df["必須/選択"].astype(str).str.strip()

    df["動画開始時間(sec)"] = pd.to_numeric(df["動画開始時間(sec)"], errors="coerce").fillna(0).astype(int)

    df["DAY"] = df["部位"].map(PART_TO_DAY).fillna("OTHER")
    df["is_required"] = df["必須/選択"].isin(["必須", "Required", "REQ"])

    # CHESTは全部必須（運用上）
    df.loc[df["DAY"] == "CHEST", "is_required"] = True

    def _urls(row):
        d = build_youtube_urls(row["動画LINK"], row["動画開始時間(sec)"])
        return pd.Series([d["embed_url"], d["watch_url"]])

    df[["video_embed_url", "video_watch_url"]] = df.apply(_urls, axis=1)
    return df
