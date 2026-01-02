import time
import io
import math
import wave
import struct

def _tone_wav_bytes(freq_hz: float, duration_sec: float, volume: float = 0.3, sr: int = 44100) -> bytes:
    """簡易ビープ音（WAV）をメモリ生成"""
    n = int(sr * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for i in range(n):
            t = i / sr
            s = volume * math.sin(2 * math.pi * freq_hz * t)
            wf.writeframes(struct.pack("<h", int(s * 32767)))
    return buf.getvalue()

BEEP_CLICK = _tone_wav_bytes(1200, 0.04, 0.25)
BEEP_START = _tone_wav_bytes(900, 0.15, 0.30)
BEEP_END   = _tone_wav_bytes(500, 0.30, 0.35)

def render_metronome_ui(st, key_prefix: str = "rope"):
    """
    UI:
      - 時間: 60/120/180（デフォルト60）
      - 間隔: 0.5/0.46/0.42/0.4（表示は標準/やや早/早い/高速）
      - Start: 3,2,1 → start beep → click → end beep
      - 目標回数を表示
    """
    durations = [60, 120, 180]
    interval_opts = [
        ("標準（0.50秒）", 0.50),
        ("やや早（0.46秒）", 0.46),
        ("早い（0.42秒）", 0.42),
        ("高速（0.40秒）", 0.40),
    ]

    col1, col2 = st.columns(2)
    with col1:
        duration = st.selectbox("時間（秒）", durations, index=0, key=f"{key_prefix}_dur")
    with col2:
        label = st.selectbox("テンポ", [x[0] for x in interval_opts], index=0, key=f"{key_prefix}_tmp")
        interval = dict(interval_opts)[label]

    target = int(round(duration / interval))
    st.caption(f"目標：{duration}秒で **{target}回**（×3セット想定）")

    if st.button("▶ リズム開始（3,2,1）", key=f"{key_prefix}_start"):
        msg = st.empty()

        # countdown
        for n in [3, 2, 1]:
            msg.markdown(f"## {n}")
            time.sleep(1.0)

        msg.markdown("## START!")
        st.audio(BEEP_START, format="audio/wav")
        time.sleep(0.2)

        start_t = time.time()
        next_t = start_t
        beats = 0

        # 実行中表示
        run = st.empty()
        progress = st.progress(0)

        while True:
            now = time.time()
            elapsed = now - start_t
            if elapsed >= duration:
                break

            # click timing
            if now >= next_t:
                beats += 1
                st.audio(BEEP_CLICK, format="audio/wav")
                next_t += interval

            # UI update
            run.write(f"経過: {elapsed:.1f}s / {duration}s   |   ビート: {beats} / 目標 {target}")
            progress.progress(min(1.0, elapsed / duration))
            time.sleep(0.01)

        st.audio(BEEP_END, format="audio/wav")
        msg.markdown("## 終了！")
        run.write(f"結果: {beats}回（目標 {target}回）")
        progress.progress(1.0)
