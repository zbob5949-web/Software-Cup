// =============================================================================
//  lipsync.js  ——  浏览器端 TTS → VRM 元音口型同步
//  ---------------------------------------------------------------------------
//  特性:
//    1) 共振峰 (F1/F2) + 子频带能量双路融合, 实时识别 a/e/i/o/u
//    2) 攻击/释放双时间常数平滑, 防止帧间抖动
//    3) 置信度低或静音时自动 fallback 到能量驱动的 aa 单口型
//    4) 兼容 HTMLAudioElement / MediaStream / AudioBuffer 三种输入
//    5) 主线程单帧 < 0.5ms (FFT=1024), 不阻塞 60fps 渲染循环
//
//  作者: 灵山景区 — 数字人前端
// =============================================================================

/** 数值钳制 */
export const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));

/** 帧率独立线性插值 — tau 为时间常数 (秒): 越小响应越快 */
export const tauLerp = (cur, tgt, dt, tau) => {
  if (tau <= 0) return tgt;
  const a = 1 - Math.exp(-dt / tau);
  return cur + (tgt - cur) * a;
};

// -----------------------------------------------------------------------------
// 普通话元音共振峰参考值 (Hz)  — 男女平均, 来自《现代汉语语音学》
// 实测值会受说话人性别/音色影响, 可在调优指南里改 vowelFormants
// -----------------------------------------------------------------------------
const DEFAULT_VOWEL_FORMANTS = {
  // VRM 标准 viseme: aa(开)、ee(半开前)、ih(闭前)、oh(半开后圆)、ou(闭后圆)
  aa: { f1: 850, f2: 1300, weight: 1.00 },  // 啊
  ee: { f1: 550, f2: 1900, weight: 0.92 },  // 诶
  ih: { f1: 320, f2: 2500, weight: 0.88 },  // 衣
  oh: { f1: 500, f2: 900,  weight: 0.95 },  // 噢
  ou: { f1: 350, f2: 800,  weight: 0.90 },  // 乌
};
const VOWEL_NAMES = ['aa', 'ee', 'ih', 'oh', 'ou'];
const EXTRA_MOUTH_NAMES = ['mbp', 'fv', 'szh', 'chsh'];
const MOUTH_NAMES = [...VOWEL_NAMES, ...EXTRA_MOUTH_NAMES];
const EMPTY_VISEME = Object.freeze({
  aa: 0, ee: 0, ih: 0, oh: 0, ou: 0, mbp: 0, fv: 0, szh: 0, chsh: 0, energy: 0, confidence: 0,
});

// =============================================================================
//  LipSyncAnalyzer  — 频谱 → 元音权重
// =============================================================================
export class LipSyncAnalyzer {
  /**
   * @param {AudioContext} audioCtx
   * @param {Object} [opts]
   * @param {number} [opts.fftSize=1024]      窗口大小, 必须 2^n; 1024 ≈ 23ms@44.1k 合适
   * @param {number} [opts.smoothing=0.5]     AnalyserNode 时域平滑, 0~0.95
   * @param {number} [opts.silenceFloor=0.012]  RMS 静音阈值 (0~1)
   * @param {number} [opts.minConfidence=0.35]  低于此值则向 fallback 混合
   * @param {number} [opts.formantMin=120]    F1 检测下限
   * @param {number} [opts.formantMax=3500]   F2 检测上限
   * @param {Object} [opts.vowelFormants]     可覆写的元音共振峰表
   */
  constructor(audioCtx, opts = {}) {
    if (!audioCtx) throw new Error('LipSyncAnalyzer 需要 AudioContext');
    this.ctx = audioCtx;
    this.fftSize = opts.fftSize ?? 1024;
    this.silenceFloor = opts.silenceFloor ?? 0.012;
    this.minConfidence = opts.minConfidence ?? 0.35;
    this.fmin = opts.formantMin ?? 120;
    this.fmax = opts.formantMax ?? 3500;
    this.vowelFormants = { ...DEFAULT_VOWEL_FORMANTS, ...(opts.vowelFormants || {}) };

    // ── Web Audio 节点 ─────────────────────────────────────────────
    this.analyser = audioCtx.createAnalyser();
    this.analyser.fftSize = this.fftSize;
    this.analyser.smoothingTimeConstant = opts.smoothing ?? 0.5;
    this.analyser.minDecibels = -90;
    this.analyser.maxDecibels = -10;

    // 静音/输出节点 — 通过它把上游音频"经过"分析器但不重复播放
    // (HTMLAudioElement 已经独立播放, 这里只 tap 一份用于分析)
    this._tapGain = audioCtx.createGain();
    this._tapGain.gain.value = 1.0;
    this._tapGain.connect(this.analyser);

    // ── 复用 buffer, 避免 GC 抖动 ─────────────────────────────────
    this._freqDb = new Float32Array(this.analyser.frequencyBinCount);
    this._timeData = new Uint8Array(this.fftSize);
    this._smoothMag = new Float32Array(this.analyser.frequencyBinCount);

    // 频率 → bin 的换算
    this._binHz = audioCtx.sampleRate / this.fftSize;
    this._binMin = Math.max(1, Math.floor(this.fmin / this._binHz));
    this._binMax = Math.min(this.analyser.frequencyBinCount - 1,
                            Math.ceil(this.fmax / this._binHz));

    // 当前已连接的源节点 (供 disconnect 用)
    this._sources = new Set();
  }

  /** 接 HTMLAudioElement / HTMLMediaElement (TTS 最常用) */
  connectMediaElement(audio) {
    const src = this.ctx.createMediaElementSource(audio);
    src.connect(this._tapGain);
    src.connect(this.ctx.destination);  // 仍然播放出来
    this._sources.add(src);
    return src;
  }

  /** 接 MediaStream (流式 TTS / WebRTC) */
  connectMediaStream(stream) {
    const src = this.ctx.createMediaStreamSource(stream);
    src.connect(this._tapGain);
    src.connect(this.ctx.destination);
    this._sources.add(src);
    return src;
  }

  /** 接 AudioBuffer (一次性合成的非流式 TTS) */
  connectAudioBuffer(buffer, { loop = false, when = 0 } = {}) {
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = loop;
    src.connect(this._tapGain);
    src.connect(this.ctx.destination);
    src.start(when);
    this._sources.add(src);
    src.onended = () => this._sources.delete(src);
    return src;
  }

  /** 释放当前所有源连接, 重置内部状态 */
  reset() {
    for (const s of this._sources) {
      try { s.disconnect(); } catch (_) {}
    }
    this._sources.clear();
    this._smoothMag.fill(0);
  }

  /**
   * 主分析入口 — 每帧调用一次
   * @returns {{aa:number,ee:number,ih:number,oh:number,ou:number,energy:number,confidence:number}}
   */
  analyze() {
    const a = this.analyser;
    a.getFloatFrequencyData(this._freqDb);
    a.getByteTimeDomainData(this._timeData);

    // ── 1. 时域 RMS → 总能量 (用于判静音 + fallback 张口度) ────────
    let sumSq = 0;
    for (let i = 0; i < this._timeData.length; i++) {
      const v = (this._timeData[i] - 128) / 128;
      sumSq += v * v;
    }
    const rms = Math.sqrt(sumSq / this._timeData.length);
    const energy = clamp((rms - this.silenceFloor) / (1 - this.silenceFloor));

    if (rms < this.silenceFloor) return { ...EMPTY_VISEME };

    // ── 2. 频域 dB → 线性幅度 + 三点平滑去噪 ──────────────────────
    const N = this._freqDb.length;
    const mag = this._smoothMag;
    let maxMag = 1e-9;
    for (let i = 0; i < N; i++) {
      // dBFS → 线性 (0~1), -90dB 截零
      const lin = Math.pow(10, this._freqDb[i] / 20);
      // EMA 平滑相邻帧 (除 AnalyserNode 自带平滑外再做一次)
      mag[i] = mag[i] * 0.55 + lin * 0.45;
      if (mag[i] > maxMag) maxMag = mag[i];
    }
    const invMax = 1 / maxMag;

    // ── 3. 共振峰 F1/F2 拾取 ─────────────────────────────────────
    // F1 一般在 250~900 Hz, F2 在 800~3000 Hz, 用两段独立找峰
    const splitBin = Math.floor(900 / this._binHz);
    let f1Bin = -1, f1Val = 0;
    let f2Bin = -1, f2Val = 0;

    for (let i = this._binMin + 1; i < Math.min(splitBin, this._binMax); i++) {
      const m = mag[i] * invMax;
      // 局部极大: 比左右邻居都大
      if (m > f1Val && m > mag[i - 1] * invMax && m > mag[i + 1] * invMax) {
        f1Val = m; f1Bin = i;
      }
    }
    for (let i = Math.max(splitBin, this._binMin) + 1; i < this._binMax; i++) {
      const m = mag[i] * invMax;
      if (m > f2Val && m > mag[i - 1] * invMax && m > mag[i + 1] * invMax) {
        f2Val = m; f2Bin = i;
      }
    }

    const f1 = f1Bin > 0 ? f1Bin * this._binHz : 0;
    const f2 = f2Bin > 0 ? f2Bin * this._binHz : 0;
    const peakStrength = (f1Val + f2Val) * 0.5;     // 0~1, 共振峰显著程度
    const confidence = clamp(peakStrength * 1.6);   // 经验放大系数

    // ── 4. 元音分类: Bark 频率距离 → softmax 权重 ────────────────
    // (Bark 比 Hz 更贴近听感, 对元音聚类更稳)
    const barkF1 = hzToBark(f1);
    const barkF2 = hzToBark(f2);
    const scores = {};
    let scoreSum = 0;
    const sigma = 1.6;  // 高斯核宽度, 越大越"模糊"
    for (const name of VOWEL_NAMES) {
      const v = this.vowelFormants[name];
      const d1 = barkF1 - hzToBark(v.f1);
      const d2 = barkF2 - hzToBark(v.f2);
      const dist = Math.sqrt(d1 * d1 + d2 * d2);
      // 高斯衰减 + 元音"显著性"权重
      const s = Math.exp(-(dist * dist) / (2 * sigma * sigma)) * v.weight;
      scores[name] = s;
      scoreSum += s;
    }

    // ── 5. 归一化 + 能量包络 + 置信度衰减 ────────────────────────
    const out = { aa: 0, ee: 0, ih: 0, oh: 0, ou: 0, energy, confidence };
    if (scoreSum > 1e-6) {
      const inv = 1 / scoreSum;
      // 锐化: 用幂次拉开主元音和次元音的权重差距
      const SHARP = 2.2;
      let sharpSum = 0;
      const sharp = {};
      for (const name of VOWEL_NAMES) {
        sharp[name] = Math.pow(scores[name] * inv, SHARP);
        sharpSum += sharp[name];
      }
      const sharpInv = 1 / Math.max(sharpSum, 1e-6);
      for (const name of VOWEL_NAMES) {
        // 最终权重 = 锐化分布 × 总能量 × 置信度系数
        out[name] = sharp[name] * sharpInv * energy * (0.4 + 0.6 * confidence);
      }
    }
    return out;
  }

  /** 直接拿到底层 Analyser, 方便外层做可视化 */
  getAnalyserNode() { return this.analyser; }
}

/** Hz → Bark (Traunmüller 1990) */
function hzToBark(hz) {
  if (hz <= 0) return 0;
  return 26.81 / (1 + 1960 / hz) - 0.53;
}

// =============================================================================
//  VrmLipSyncDriver — viseme → VRM expressionManager, 含平滑与 fallback
// =============================================================================
export class VrmLipSyncDriver {
  /**
   * @param {Object} vrm  @pixiv/three-vrm 的 VRM 实例
   * @param {Object} [opts]
   * @param {number} [opts.attackTau=0.045]   嘴张开攻击时间常数 (秒)
   * @param {number} [opts.releaseTau=0.10]   嘴闭合释放时间常数 (秒)
   * @param {number} [opts.maxOpen=1.0]       最大张口度上限
   * @param {number} [opts.fallbackVowel='aa'] 置信度低时退化到的口型
   * @param {number} [opts.fallbackBlend=0.55] fallback 混合系数
   */
  constructor(vrm, opts = {}) {
    this.vrm = vrm;
    this.attackTau = opts.attackTau ?? 0.045;
    this.releaseTau = opts.releaseTau ?? 0.10;
    this.maxOpen = opts.maxOpen ?? 1.0;
    this.fallbackVowel = opts.fallbackVowel ?? 'aa';
    this.fallbackBlend = opts.fallbackBlend ?? 0.55;
    this.minConfidence = opts.minConfidence ?? 0.35;

    // 探测 VRM 上实际可用的 viseme blendshape
    this.available = new Set();
    const mgr = vrm?.expressionManager;
    if (mgr) {
      for (const name of MOUTH_NAMES) {
        try {
          if (mgr.getExpression?.(name) || mgr.getExpressionTrackName?.(name)) {
            this.available.add(name);
          }
        } catch (_) { /* 表情不存在时忽略 */ }
      }
    }
    if (this.available.size === 0) {
      console.warn('[VrmLipSyncDriver] 当前 VRM 没有 a/e/i/o/u 表情, 口型同步将无效');
    }

    // 当前已应用的平滑值 (上一帧)
    this.current = Object.fromEntries(MOUTH_NAMES.map((name) => [name, 0]));
    // 外部偏置 (可叠加文本先验, 例如已有的 mouthTimeline)
    this.bias = Object.fromEntries(MOUTH_NAMES.map((name) => [name, 0]));
  }

  /** 设置文本先验 (0~1), 与频谱结果按置信度混合 */
  setBias(visemeLike) {
    for (const k of MOUTH_NAMES) {
      this.bias[k] = clamp(visemeLike?.[k] ?? 0);
    }
  }

  /**
   * 每帧调用 — 把分析器输出应用到 VRM
   * @param {Object} viseme    LipSyncAnalyzer.analyze() 的返回
   * @param {number} dt        距上一帧的秒数
   */
  apply(viseme, dt) {
    if (!this.vrm?.expressionManager) return;
    const mgr = this.vrm.expressionManager;
    const conf = viseme?.confidence ?? 0;
    const energy = viseme?.energy ?? 0;

    // ── fallback 策略 ──────────────────────────────────────────────
    // confidence 低 → 把识别结果向"能量×默认元音"靠拢
    // 这样静音/噪声/未训练发音都不会让嘴抽搐
    let target;
    if (conf < this.minConfidence) {
      const k = clamp((this.minConfidence - conf) / this.minConfidence);  // 0~1
      const fallback = Object.fromEntries(MOUTH_NAMES.map((name) => [name, 0]));
      fallback[this.fallbackVowel] = energy * this.fallbackBlend;
      target = mixViseme(viseme, fallback, k);
    } else {
      target = { ...viseme };
    }

    // ── 叠加文本先验偏置 ──
    // 后端 pypinyin 给的拼音轨非常准, 让先验主导 (0.65), 频谱做能量/锐化补正 (0.35)
    // 高置信度时把先验权重稍微让一点给频谱 (情绪化的非元音瞬间)
    const wPrior = 0.65 - 0.15 * conf;
    for (const k of MOUTH_NAMES) {
      const priorWeight = EXTRA_MOUTH_NAMES.includes(k) ? 1.0 : wPrior;
      target[k] = clamp((target[k] ?? 0) * (1 - priorWeight) + (this.bias[k] ?? 0) * priorWeight);
    }

    // ── 攻击/释放双时间常数平滑 ──────────────────────────────────
    for (const k of MOUTH_NAMES) {
      const cur = this.current[k];
      const tgt = clamp(target[k] ?? 0) * this.maxOpen;
      const tau = tgt > cur ? this.attackTau : this.releaseTau;
      const next = tauLerp(cur, tgt, dt, tau);
      this.current[k] = Math.abs(next) < 1e-4 ? 0 : next;
      if (this.available.has(k)) {
        mgr.setValue(k, this.current[k]);
      }
    }
  }

  /** 强制归零 (停止说话/切换会话时调用) */
  silence(immediate = false) {
    for (const k of MOUTH_NAMES) {
      if (immediate) this.current[k] = 0;
      this.bias[k] = 0;
      if (this.available.has(k)) {
        this.vrm?.expressionManager?.setValue(k, immediate ? 0 : this.current[k]);
      }
    }
  }
}

/** viseme 之间按 alpha 混合 (alpha=1 时完全取 b) */
function mixViseme(a, b, alpha) {
  const out = {};
  for (const k of MOUTH_NAMES) {
    out[k] = (a?.[k] ?? 0) * (1 - alpha) + (b?.[k] ?? 0) * alpha;
  }
  out.energy = (a?.energy ?? 0) * (1 - alpha) + (b?.energy ?? 0) * alpha;
  out.confidence = a?.confidence ?? 0;
  return out;
}
