import streamlit as st

def render_breath_ui(st, key_prefix: str = "breath"):
    """
    体幹DAYの冒頭で行う呼吸法ガイド（45秒 = 15秒×3セット）
    - 1周45秒で進捗が塗られていく円形インジケータ（45セグメント）
    - Startボタン押下 → 3,2,1 カウントダウン → 描画と音が同期して開始
    - 音は Web Audio API（発振）で軽量・安定運用（外部音源不要）

    セット構成（15秒を3回）：
      0-3秒  : 吸う（緑）  4秒
      4-11秒 : 吐く（赤）  8秒
      12-14秒: 通常（青） 3秒
    """

    k_run = f"{key_prefix}_run"

    st.subheader("呼吸法（45秒）")
    st.caption("Startを押して、3-2-1の後に開始します（吸う4秒 → 吐く8秒 → 通常3秒 を3セット連続）。")

    bcol1, bcol2 = st.columns([1, 1])

    with bcol1:
        if st.button("▶ Start（3,2,1→開始）", key=f"{key_prefix}_start"):
            st.session_state[k_run] = True

    with bcol2:
        if st.button("■ Stop", key=f"{key_prefix}_stop"):
            st.session_state[k_run] = False

    if not st.session_state.get(k_run, False):
        st.info("Startを押すと、呼吸ガイドが始まります。")
        return

    # JS側でタイマー・描画・音を完結させる（Streamlit rerunの影響を受けない）
    html = f"""
    <div style="display:flex; flex-direction:column; gap:10px; align-items:center; justify-content:center; width:100%;">
      <div id="{key_prefix}_status" style="font-size:14px; font-weight:600;"></div>

      <svg id="{key_prefix}_svg" width="220" height="220" viewBox="0 0 220 220" role="img" aria-label="Breathing indicator">
        <circle cx="110" cy="110" r="92" fill="none" stroke="rgba(160,160,160,0.25)" stroke-width="10"></circle>
        <g id="{key_prefix}_segments"></g>

        <circle cx="110" cy="110" r="55" fill="rgba(255,255,255,0.03)" stroke="rgba(160,160,160,0.15)" stroke-width="1"></circle>
        <text id="{key_prefix}_phase" x="110" y="110" text-anchor="middle" dominant-baseline="middle"
              style="font-size:16px; font-weight:700; fill:rgba(240,240,240,0.9);">
          準備…
        </text>
        <text id="{key_prefix}_timer" x="110" y="135" text-anchor="middle" dominant-baseline="middle"
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
      const total = 45;      // 45 sec
      const perSet = 15;     // 15 sec
      const inhaleLen = 4;   // sec
      const exhaleLen = 8;   // sec

      const statusEl = document.getElementById("{key_prefix}_status");
      const segRoot  = document.getElementById("{key_prefix}_segments");
      const phaseEl  = document.getElementById("{key_prefix}_phase");
      const timerEl  = document.getElementById("{key_prefix}_timer");

      // ---------- SVG segments ----------
      const cx = 110, cy = 110;
      const rOuter = 95;
      const rInner = 85;
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
        path.setAttribute("stroke", "rgba(0,0,0,0)");
        segRoot.appendChild(path);
        segEls.push(path);
      }}

      function phaseColor(phase) {{
        // phase: 0..14 within a set
        if (phase >= 0 && phase <= 3)  return "rgba(60, 200, 120, 0.95)"; // green
        if (phase >= 4 && phase <= 11) return "rgba(235, 90, 90, 0.95)";  // red
        return "rgba(80, 170, 255, 0.95)"; // blue (12..14)
      }}

      function phaseLabel(phase) {{
        if (phase >= 0 && phase <= 3)  return "吸う（4秒）";
        if (phase >= 4 && phase <= 11) return "吐く（8秒）";
        return "通常呼吸（3秒）";
      }}

      function paintProgress(t) {{
        // t: 0..44
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

      function sleep(ms) {{
        return new Promise(resolve => setTimeout(resolve, ms));
      }}

      // ---------- WebAudio ----------
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

      function tone(freq, durationMs, gain=0.06) {{
        // gentle continuous tone
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
        // slight decay at the end
        g.gain.linearRampToValueAtTime(0.0001, now + durationMs / 1000.0);

        o.start(now);
        o.stop(now + durationMs / 1000.0 + 0.03);
      }}

      // ---------- Runner ----------
      async function run() {{
        // countdown
        const countdown = [3,2,1];
        for (let i=0; i<countdown.length; i++) {{
          setStatus("開始まで " + countdown[i] + "…");
          phaseEl.textContent = "準備…";
          timerEl.textContent = "0 / " + total;
          beep(520, 120, 0.12);
          await sleep(1000);
        }}

        // start marker
        setStatus("開始！");
        beep(660, 160, 0.14);
        await sleep(120);

        for (let t=0; t<total; t++) {{
          paintProgress(t);

          const p = t % perSet;

          // phase sounds
          if (p === 0) {{
            // inhale 4 sec
            tone(420, inhaleLen * 1000, 0.055);
          }} else if (p === inhaleLen) {{
            // exhale 8 sec (p==4)
            tone(260, exhaleLen * 1000, 0.05);
          }} else if (p >= inhaleLen + exhaleLen) {{
            // normal breathing 3 sec (p==12,13,14): short beeps each second
            beep(880, 90, 0.11);
          }}

          await sleep(1000);
        }}

        // end
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

    st.components.v1.html(html, height=320, key=f"{key_prefix}_html")
