import time
import streamlit as st

def _calc_target_reps(duration_sec: int, interval_sec: float) -> int:
    if interval_sec <= 0:
        return 0
    return int(round(duration_sec / interval_sec))

def render_metronome_ui(st, key_prefix: str = "metronome"):
    """
    縄跳び用メトロノームUI
    - 「▶ 再生」ボタンを押す → 3,2,1 → 開始音 → メトロノーム → 終了音
    - UX重視：バーが大量に出ないように、Streamlit標準の st.audio を連打しない
      （WebAudio + HTMLで鳴らす）
    """

    # =========================
    # 設定（UI表示）
    # =========================
    duration_options = {
        "60秒（推奨）": 60,
        "120秒": 120,
        "180秒": 180,
    }

    tempo_options = {
        "標準（0.50秒）": 0.50,   # 120回/60秒
        "やや早（0.46秒）": 0.46,
        "早い（0.42秒）": 0.42,
        "高速（0.40秒）": 0.40,   # 150回/60秒
    }

    # =========================
    # セッション状態キー
    # =========================
    k_run = f"{key_prefix}_run"
    k_started_at = f"{key_prefix}_started_at"
    k_duration = f"{key_prefix}_duration"
    k_interval = f"{key_prefix}_interval"

    if k_run not in st.session_state:
        st.session_state[k_run] = False

    # =========================
    # UI（選択）
    # =========================
    c1, c2 = st.columns(2)
    with c1:
        duration_label = st.selectbox(
            "時間（秒）",
            list(duration_options.keys()),
            index=0,
            key=f"{key_prefix}_duration_select",
        )
        duration_sec = duration_options[duration_label]

    with c2:
        tempo_label = st.selectbox(
            "リズム（テンポ）",
            list(tempo_options.keys()),
            index=0,
            key=f"{key_prefix}_tempo_select",
        )
        interval_sec = tempo_options[tempo_label]

    target_reps = _calc_target_reps(duration_sec, interval_sec)
    st.caption(f"目安回数：**{target_reps}回**（{duration_sec}秒 ÷ {interval_sec:.2f}秒）")

    # =========================
    # ▶ 再生ボタンで開始（要望対応）
    # =========================
    bcol1, bcol2 = st.columns([1, 1])

    with bcol1:
        if st.button("▶ 再生（3,2,1→開始）", key=f"{key_prefix}_play"):
            st.session_state[k_run] = True
            st.session_state[k_started_at] = time.time()
            st.session_state[k_duration] = int(duration_sec)
            st.session_state[k_interval] = float(interval_sec)

    with bcol2:
        if st.button("■ 停止", key=f"{key_prefix}_stop"):
            st.session_state[k_run] = False

    # =========================
    # 実行中：HTML(WebAudio)で音を鳴らす
    # =========================
    if not st.session_state.get(k_run, False):
        return

    started_at = float(st.session_state.get(k_started_at, time.time()))
    duration_sec = int(st.session_state.get(k_duration, duration_sec))
    interval_sec = float(st.session_state.get(k_interval, interval_sec))

    # ここで「押した瞬間に」カウントダウンを含む処理を開始する
    # Streamlitは1回描画して終わるので、JS側で時間管理する
    # （バー大量表示の原因になる st.audio の連打はしない）

    html = f"""
    <div style="padding:12px 10px;border:1px solid #ddd;border-radius:10px;">
      <div style="font-size:18px;font-weight:700;margin-bottom:6px;">
        縄跳びメトロノーム（{duration_sec}秒 / {interval_sec:.2f}秒）
      </div>
      <div id="status" style="font-size:16px;margin-bottom:8px;">準備中…</div>
      <div style="font-size:14px;color:#666;">
        ※ 音が出ない場合：端末の消音、Bluetooth、ブラウザの自動再生制限をご確認ください。
      </div>
    </div>

    <script>
      (function() {{
        // 二重起動を避けるため、毎回ユニークIDを作る
        const uid = "{key_prefix}_{int(time.time()*1000)}";
        const statusEl = document.getElementById("status");

        // WebAudio
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContext();

        function beep(freq, ms, gainVal) {{
          const o = ctx.createOscillator();
          const g = ctx.createGain();
          o.type = "sine";
          o.frequency.value = freq;
          g.gain.value = gainVal;
          o.connect(g);
          g.connect(ctx.destination);
          o.start();
          setTimeout(() => {{
            o.stop();
          }}, ms);
        }}

        // iOS等で必要：ユーザー操作直後にresume
        ctx.resume().catch(()=>{{}});

        const durationSec = {duration_sec};
        const intervalSec = {interval_sec};

        // 3,2,1 カウントダウン → 開始音 → tick → 終了音
        const countdown = [3,2,1];

        function setStatus(t) {{
          if (statusEl) statusEl.innerText = t;
        }}

        function sleep(ms) {{
          return new Promise(resolve => setTimeout(resolve, ms));
        }}

        async function run() {{
          // countdown
          for (let i=0; i<countdown.length; i++) {{
            setStatus("開始まで " + countdown[i] + "…");
            beep(520, 120, 0.15);
            await sleep(1000);
          }}

          // start
          setStatus("スタート！");
          beep(880, 180, 0.20);

          const start = performance.now();
          const end = start + durationSec*1000;
          let next = start;
          let count = 0;

          while (performance.now() < end) {{
            const now = performance.now();
            if (now >= next) {{
              // tick
              beep(740, 70, 0.12);
              count++;
              next += intervalSec*1000;
              const remain = Math.max(0, Math.ceil((end - now)/1000));
              setStatus("実行中… 残り " + remain + " 秒（目安 " + count + " 回）");
            }}
            await sleep(5);
          }}

          // end
          setStatus("終了！");
          beep(440, 250, 0.18);
          await sleep(150);
          beep(440, 250, 0.18);
        }}

        run();
      }})();
    </script>
    """

    st.components.v1.html(html, height=150)
