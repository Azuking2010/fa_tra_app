# metronome_component.py
# Streamlit用：縄跳びメトロノーム（Web Audio API）
# - Start押下 → 3,2,1 → 開始音 → メトロノーム → 終了音
# - Python側でsleepせず、ブラウザ側(JS)でタイミング制御（Streamlitで安定）

import streamlit.components.v1 as components


def _round_int(x: float) -> int:
    return int(round(x))


def calc_target_jumps(duration_sec: int, interval_sec: float) -> int:
    """時間×間隔から「目標回数」を算出（四捨五入）"""
    if interval_sec <= 0:
        return 0
    return _round_int(duration_sec / interval_sec)


def render_jump_rope_metronome(
    duration_sec: int = 60,
    interval_sec: float = 0.5,
    countdown_sec: int = 3,
    sound: str = "beep",  # "beep" or "click"
    height: int = 170,
    key: str = "jump_rope_metronome",
):
    """
    Streamlit上で動作するメトロノームUIを描画する（JS/HTML）。
    戻り値なし（表示のみ）。
    """
    duration_sec = int(duration_sec)
    countdown_sec = int(countdown_sec)
    interval_sec = float(interval_sec)
    sound = sound if sound in ("beep", "click") else "beep"

    target = calc_target_jumps(duration_sec, interval_sec)

    # JS側で小数intervalのsetIntervalはズレるので、"次の予定時刻"方式で補正しながら鳴らす
    # （performance.now()を使ったスケジューリング）
    html = f"""
    <div id="{key}" style="font-family: sans-serif; font-size: 18px;">
      <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
        <button id="{key}_start" style="font-size:18px;padding:10px 14px;">Start</button>
        <button id="{key}_stop" style="font-size:18px;padding:10px 14px;" disabled>Stop</button>
        <div style="font-size:20px;">残り: <span id="{key}_left">{duration_sec}</span>s</div>
        <div style="font-size:20px;">状態: <span id="{key}_state">待機</span></div>
      </div>

      <div style="margin-top:10px; display:flex; gap:16px; flex-wrap:wrap;">
        <div style="font-size:22px;">カウント: <span id="{key}_count">-</span></div>
        <div style="font-size:22px;">拍数: <span id="{key}_ticks">0</span> / {target}</div>
      </div>

      <div style="margin-top:6px; font-size:14px; opacity:0.75;">
        ※ iPhone/Safariは「Start」押下などのユーザー操作がないと音が鳴りません
      </div>
    </div>

    <script>
    (function() {{
      const root = document.getElementById("{key}");
      if (!root) return;

      const durationSec = {duration_sec};
      const countdownSec = {countdown_sec};
      const intervalSec = {interval_sec};
      const soundMode = "{sound}";

      const startBtn = document.getElementById("{key}_start");
      const stopBtn  = document.getElementById("{key}_stop");
      const leftEl   = document.getElementById("{key}_left");
      const stateEl  = document.getElementById("{key}_state");
      const countEl  = document.getElementById("{key}_count");
      const ticksEl  = document.getElementById("{key}_ticks");

      let audioCtx = null;
      let running = false;

      let timerId = null;   // 1秒カウントダウン/残り時間用
      let tickRAF = null;   // requestAnimationFrame で拍のスケジューリング
      let nextTickTime = 0; // 次に鳴らすべき時間(ms, performance.now基準)
      let ticks = 0;

      function getCtx() {{
        if (!audioCtx) {{
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }}
        return audioCtx;
      }}

      function tone(freq, ms, gainVal=0.25) {{
        const ctx = getCtx();
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = "sine";
        o.frequency.value = freq;
        g.gain.value = gainVal;
        o.connect(g); g.connect(ctx.destination);
        o.start();
        setTimeout(() => {{
          try {{ o.stop(); }} catch(e) {{}}
        }}, ms);
      }}

      function click(ms=18) {{
        const ctx = getCtx();
        const bufferSize = Math.max(1, Math.floor(ctx.sampleRate * (ms/1000)));
        const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i=0; i<data.length; i++) {{
          data[i] = (Math.random()*2-1) * 0.22 * (1 - i/data.length);
        }}
        const src = ctx.createBufferSource();
        src.buffer = buffer;
        src.connect(ctx.destination);
        src.start();
      }}

      function startBeep() {{
        tone(880, 120, 0.35);
      }}

      function endBuzz() {{
        tone(440, 140, 0.35);
        setTimeout(() => tone(440, 140, 0.35), 180);
      }}

      function tick() {{
        if (soundMode === "click") {{
          click(18);
        }} else {{
          tone(1000, 35, 0.18);
        }}
      }}

      function setState(s) {{
        stateEl.textContent = s;
      }}

      function resetUI() {{
        leftEl.textContent = String(durationSec);
        countEl.textContent = "-";
        ticksEl.textContent = "0";
        ticks = 0;
        setState("待機");
        startBtn.disabled = false;
        stopBtn.disabled = true;
      }}

      function stopAll() {{
        if (timerId) {{ clearInterval(timerId); timerId = null; }}
        if (tickRAF) {{ cancelAnimationFrame(tickRAF); tickRAF = null; }}
        running = false;
        resetUI();
      }}

      function scheduleTicks() {{
        if (!running) return;

        const now = performance.now();
        // intervalSec(秒) → ms
        const intervalMs = intervalSec * 1000;

        // 予定時刻に追いついたら鳴らす（複数遅れをまとめて処理）
        while (now >= nextTickTime) {{
          tick();
          ticks += 1;
          ticksEl.textContent = String(ticks);
          nextTickTime += intervalMs;
        }}

        tickRAF = requestAnimationFrame(scheduleTicks);
      }}

      async function run() {{
        if (running) return;
        running = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;

        // iOS対策：ユーザー操作直後にresume
        const ctx = getCtx();
        if (ctx.state === "suspended") {{
          try {{ await ctx.resume(); }} catch(e) {{}}
        }}

        // countdown
        setState("カウントダウン");
        for (let i = countdownSec; i >= 1; i--) {{
          countEl.textContent = String(i);
          tone(660, 90, 0.25);
          await new Promise(r => setTimeout(r, 1000));
          if (!running) return;
        }}
        countEl.textContent = "GO!";
        startBeep();
        setState("実行中");

        // 残り時間
        let left = durationSec;
        leftEl.textContent = String(left);

        // 拍の開始
        ticks = 0;
        ticksEl.textContent = "0";
        nextTickTime = performance.now(); // すぐ1発目
        scheduleTicks();

        // 1秒ごとに残り時間を更新
        timerId = setInterval(() => {{
          left -= 1;
          leftEl.textContent = String(Math.max(left, 0));
          if (left <= 0) {{
            endBuzz();
            stopAll();
          }}
        }}, 1000);
      }}

      startBtn.addEventListener("click", run);
      stopBtn.addEventListener("click", () => stopAll());

      resetUI();
    }})();
    </script>
    """
    components.html(html, height=height)
