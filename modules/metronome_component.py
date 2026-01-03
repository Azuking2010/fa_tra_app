# modules/metronome_component.py
import math
import wave
import struct
import io

import streamlit as st
import streamlit.components.v1 as components


def _tone(freq_hz: float, sec: float, sr: int = 44100, vol: float = 0.35) -> list[int]:
    n = max(1, int(sr * sec))
    out = []
    # クリック感を出すため、ほんの少しだけ減衰（クリックの耳障り軽減）
    for i in range(n):
        t = i / sr
        env = 1.0 - (i / n) * 0.35
        v = vol * env * math.sin(2.0 * math.pi * freq_hz * t)
        out.append(int(max(-1.0, min(1.0, v)) * 32767))
    return out


def _silence(sec: float, sr: int = 44100) -> list[int]:
    n = max(1, int(sr * sec))
    return [0] * n


def _to_wav_bytes(samples: list[int], sr: int = 44100) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        frames = b"".join(struct.pack("<h", s) for s in samples)
        wf.writeframes(frames)
    return buf.getvalue()


def build_metronome_wav(duration_sec: int, interval_sec: float, sr: int = 44100) -> bytes:
    """
    3,2,1（1秒間隔の短いビープ）→ メトロノーム（指定間隔）→ 終了ビープ
    を1本のWAVに合成して返す
    """
    # 音色
    beep = _tone(880, 0.07, sr=sr, vol=0.45)     # カウントダウン/開始
    click = _tone(1200, 0.03, sr=sr, vol=0.35)   # メトロノーム（短いクリック）
    end_beep = _tone(660, 0.25, sr=sr, vol=0.45) # 終了

    samples: list[int] = []

    # 3,2,1：ビープ→残りを無音で1秒にそろえる
    for _ in range(3):
        samples += beep
        samples += _silence(max(0.0, 1.0 - (len(beep) / sr)), sr=sr)

    # メトロノーム本体
    beats = int(round(duration_sec / interval_sec))
    for _ in range(beats):
        samples += click
        rest = max(0.0, interval_sec - (len(click) / sr))
        samples += _silence(rest, sr=sr)

    # 終了音
    samples += end_beep

    return _to_wav_bytes(samples, sr=sr)


def _audio_autoplay_html(wav_bytes: bytes, key: str) -> str:
    # base64にして audio tag で1個だけ鳴らす（ボタン押下直後なら自動再生が通りやすい）
    import base64
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    # keyはDOM idの衝突回避
    return f"""
    <audio id="m_{key}" autoplay>
      <source src="data:audio/wav;base64,{b64}" type="audio/wav">
    </audio>
    <script>
      const a = document.getElementById("m_{key}");
      // 自動再生がブロックされた場合に備えてplay()も試す
      if (a) {{
        const p = a.play();
        if (p !== undefined) {{
          p.catch(() => {{}});
        }}
      }}
    </script>
    """


def render_metronome_ui(st, key_prefix: str = "rope"):
    st.caption("時間とテンポを選んで ▶開始。3,2,1 のあとにメトロノームが鳴ります。")

    duration = st.selectbox(
        "時間（秒）",
        [60, 120, 180],
        index=0,
        key=f"{key_prefix}_dur",
    )

    tempo_map = {
        "標準（0.50s）": 0.50,
        "やや早（0.46s）": 0.46,
        "早い（0.42s）": 0.42,
        "高速（0.40s）": 0.40,
    }
    tempo_label = st.selectbox(
        "テンポ",
        list(tempo_map.keys()),
        index=0,
        key=f"{key_prefix}_tempo",
    )
    interval = tempo_map[tempo_label]

    expected = int(round(duration / interval))
    st.write(f"目安回数：**{expected} 回**（{duration}秒 / {interval:.2f}秒）")

    # ※ st.form の中では st.button が使えないので、ここは“フォーム外”で呼ばれる前提
    if st.button("▶ リズム開始（3,2,1 → メトロノーム）", key=f"{key_prefix}_start"):
        wav = build_metronome_wav(duration_sec=duration, interval_sec=interval)

        # 1) 自動再生（推奨）
        components.html(_audio_autoplay_html(wav, key=f"{key_prefix}_{duration}_{tempo_label}"), height=0)

        # 2) 自動再生がブロックされた時の保険（1個だけ）
        st.audio(wav, format="audio/wav")

        st.info("自動再生されない場合は、下の再生ボタン（▶）を1回押してください。")
