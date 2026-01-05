import streamlit as st


def render_breath_ui(st, key_prefix: str = "breath"):
    """
    体幹DAY冒頭用 呼吸法ガイド（45秒＝15秒×3セット）
    - 円形45セグメント：進捗が塗られていく
    - Start→3,2,1→開始（描画と音を同期）
    - 音はWebAudio発振で軽量・安定（外部音源不要）

    1セット（15秒）：
      0-3秒  : 吸う（緑）4秒
      4-11秒 : 吐く（赤）8秒
      12-14秒: 通常（青）3秒
    """

    k_run = f"{key_prefix}_run"
    st.subheader("呼吸法（45秒）")
    st.caption("Startを押す → 3-2-1 → 開始（吸う4秒 → 吐く8秒 → 通常3秒 ×3セット）")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("▶ Start（3,2,1→開始）", key=f"{key_prefix}_start"):
            st.session_state[k_run] = True
    with col2:
        if st.button("■ Stop", key=f"{key_prefix}_stop"):
            st.session_state[k_run] = False

    if not st.session_state.get(k_run, False):
        st.info("Startを押すと呼吸ガイドが始まります。")
        return

    html = f"""
    <div style="display:flex; flex-direction:column; gap:10px; align-items:center; justify-content:center; width:100%;">
      <div id="{key_prefix}_status" style="font-size:14px; font-weight:600;"></div>

      <svg id="{key_prefix}_svg" width="240" height="240" viewBox="0 0 240 240" role="img" aria-label="Breathing indicator">
        <circle cx="120" cy="120" r="100" fill="none" stroke="rgba(160,160,160,0.25)" stroke-width="10"></circle>
        <g id="{key_prefix}_segments"></g>

        <circle cx="120" cy="120" r="58" fill="rgba(255,255,255,0.03)" stroke="rgba(160,160,160,0.15)" stroke-width="1"></circle>
        <text id="{key_prefix}_phase" x="120" y="120" text-anchor="middle" dominant-baseline="middle"
              style="font-size:16px; font-weight:700; fill:rgba(240,240,240,0.9);">
          準備…
        </text>
        <text id="{key_prefix}_timer" x="120" y="146" text-anchor="middle" dominant-baseline="middle"
              style="font-size:12px; font-weight:600; fill:rgba(240,240,240,0.75);">
          0 / 45
        </text>
      </svg>

      <div style="font-size:12px; color:rgba(240,240,240,0.75);">
        姿勢：立位・膝を軽く緩める・頭が上に引っ張られる感覚
      </div>
    </div>

    <script>
    (function() {{
      const total = 45;
      const perSet = 15;
      const inhaleLen = 4;
      const exhaleLen = 8;

      const statusEl = document.getElementById("{key_prefix}_status");
      const segRoot  = document.getElementById("{key_prefix}_segments");
      const phaseEl  = document.getElementById("{key_prefix}_phase");
      const timerEl  = document.getElementById("{key_prefix}_timer");

      // ----- SVG segments -----
      const cx = 120, cy = 120;
      const rOuter = 104;
      const rInner = 92;
      const segCount = total; // 45 segments
      const baseColor = "rgba(180,180,180,0.18)";

      function polarToXY(cx, cy, r, deg) {{
        const rad = (deg - 90) * Math.PI / 180.0;
        return {{ x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }};
      }}

      function describeArcSegment(i, segCount, rOuter, rInner) {{
        const segDeg = 360 / segCount; // 8 deg
        const start = i * segDeg;
        const end   = (i + 1) * segDeg;

        const p1 = polarToXY(cx, cy, rOuter, start);
        const p2 = polarToXY(cx, cy, rOuter, end);
        const p3 = polarToXY(cx, cy, rInner, end);
        const p4 = polarToXY(cx, cy, rInner, start);

        const largeArc = segDeg > 180 ? 1 : 0;

        return [
          "M", p1.x, p1.y,
          "A", rOuter, rOuter, 0, largeArc, 1, p2.x, p2.y,
          "L", p3.x, p3.y,
          "A", rInner, rInner, 0, largeArc, 0, p4.x, p4.y,
          "Z"
        ].join(" ");
      }}

      const segEls = [];
      for (let i=0; i<segCount; i++) {{
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", describeArcSegment(i, segCount, rOuter, rInner));
        path.setAttribute("fill", baseColor);
        segRoot.appendChild(path);
        segEls.push(path);
      }}

      function phaseColor(phase) {{
        if (phase >= 0 && phase <= 3)  return "rgba(60, 200, 120, 0.95)"; // inhale
        if (phase >= 4 && phase <= 11) return "rgba(235, 90, 90, 0.95)";  // exhale
        return "rgba(80, 170, 255, 0.95)"; // normal
      }}

      function phaseLabel(phase) {{
        if (phase >= 0 && phase <= 3)  return "吸う（4秒）";
        if (phase >= 4 && phase <= 11) return "吐く（8秒）";
        return "通常呼吸（3秒）";
      }}

      function paintProgress(t) {{
        for (let i=0; i<segCount; i++) {{
          if (i <= t) {{
            const p = i % perSet;
            segEls[i].setAttribute("fill", phaseColor(p));
          }} else {{
            segEls[i].setAttribute("fill", baseColor);
          }}
        }}
        const pNow = t % perSet;
        phaseEl.textContent = phaseLabel(pNow);
        timerEl.textContent = (t + 1) + " / " + total;
      }}

      function setStatus(msg) {{
        if (statusEl) statusEl.textContent = msg;
      }}

      const sleep = (ms) => new Promise(r => setTimeout(r, ms));

      // ----- WebAudio -----
      let audioCtx = null;

      function ensureAudio() {{
        if (audioCtx) return audioCtx;
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        return audioCtx;
      }}

      function beep(freq, durationMs, gain=0.12) {{
        const ctx = ensureAudio();
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = "sine";
        o.frequency.value = freq;
        g.gain.value = 0.0001;
        o.connect(g);
        g.connect(ctx.destination);

        const now = ctx.currentTime;
        g.gain.setValueAtTime(0.0001, now);
        g.gain.linearRampToValueAtTime(gain, now + 0.01);
        g.gain.linearRampToValueAtTime(0.0001, now + durationMs / 1000.0);

        o.start(now);
        o.stop(now + durationMs / 1000.0 + 0.02);
      }}

      function tone(freq, durationMs, gain=0.055) {{
        const ctx = ensureAudio();
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = "sine";
        o.frequency.value = freq;
        g.gain.value = 0.0001;
        o.connect(g);
        g.connect(ctx.destination);

        const now = ctx.currentTime;
        g.gain.setValueAtTime(0.0001, now);
        g.gain.linearRampToValueAtTime(gain, now + 0.05);
        g.gain.linearRampToValueAtTime(0.0001, now + durationMs / 1000.0);

        o.start(now);
        o.stop(now + durationMs / 1000.0 + 0.03);
      }}

      async function run() {{
        const countdown = [3,2,1];
        for (let i=0; i<countdown.length; i++) {{
          setStatus("開始まで " + countdown[i] + "…");
          phaseEl.textContent = "準備…";
          timerEl.textContent = "0 / " + total;
          beep(520, 120, 0.12);
          await sleep(1000);
        }}

        setStatus("開始！");
        beep(660, 160, 0.14);
        await sleep(120);

        for (let t=0; t<total; t++) {{
          paintProgress(t);
          const p = t % perSet;

          if (p === 0) {{
            tone(420, inhaleLen * 1000, 0.055);
          }} else if (p === inhaleLen) {{
            tone(260, exhaleLen * 1000, 0.05);
          }} else if (p >= inhaleLen + exhaleLen) {{
            beep(880, 90, 0.11);
          }}

          await sleep(1000);
        }}

        setStatus("完了！");
        phaseEl.textContent = "完了！";
        timerEl.textContent = total + " / " + total;
        beep(440, 220, 0.14);
        await sleep(150);
        beep(440, 220, 0.14);
      }}

      run();
    }})();
    </script>
    """
    st.components.v1.html(html, height=360)

