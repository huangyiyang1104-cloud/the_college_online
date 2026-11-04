/**
 * 浏览器 PCM 录音 → 16k 单声道 WAV 分段。
 *
 * 为什么不用 MediaRecorder：
 *   它输出 webm/opus，腾讯云一句话识别不支持 webm；转码要 ffmpeg，得不偿失。
 * 为什么手工拼 WAV 头：
 *   getUserMedia 拿到的本来就是 PCM，补 44 字节头即可，后端拿到能直接送识别。
 * 为什么用 ScriptProcessor：
 *   兼容性最好、代码最短（已废弃但主流浏览器仍支持）；需要时换成 AudioWorklet，接口不变。
 */

export type SegmentHandler = (wav: Blob, index: number) => void

export interface PcmRecorderOptions {
  /** 单段上限（秒），满即切段上传，默认 55（腾讯云上限 60） */
  max_seconds?: number
  on_segment: SegmentHandler
}

export interface PcmRecorder {
  start: () => Promise<void>
  stop: () => Promise<void>
  dispose: () => void
  is_recording: () => boolean
  seconds: () => number
}

const TARGET_RATE = 16000
const MIN_SEGMENT_SECONDS = 0.5

/** 线性插值重采样：Safari 等可能忽略 AudioContext 的 sampleRate 参数 */
function downsample(input: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return input
  const ratio = from / to
  const length = Math.floor(input.length / ratio)
  const output = new Float32Array(length)
  for (let i = 0; i < length; i++) {
    const pos = i * ratio
    const idx = Math.floor(pos)
    const frac = pos - idx
    const next = idx + 1 < input.length ? idx + 1 : idx
    output[i] = input[idx] * (1 - frac) + input[next] * frac
  }
  return output
}

/** 16bit 单声道 WAV 封装 */
export function encode_wav(samples: Int16Array, sample_rate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  const write_str = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i))
    }
  }

  write_str(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  write_str(8, 'WAVE')
  write_str(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // 单声道
  view.setUint32(24, sample_rate, true)
  view.setUint32(28, sample_rate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  write_str(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++, offset += 2) {
    view.setInt16(offset, samples[i], true)
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

export function use_pcm_recorder(options: PcmRecorderOptions): PcmRecorder {
  const max_seconds = options.max_seconds ?? 55

  let stream: MediaStream | null = null
  let ctx: AudioContext | null = null
  let source: MediaStreamAudioSourceNode | null = null
  let processor: ScriptProcessorNode | null = null
  let sink: GainNode | null = null

  let chunks: Int16Array[] = []
  let buffered = 0
  let segment_index = 0
  let recording = false
  let started_at = 0

  function flush(force: boolean) {
    if (!buffered) return
    // 太短（咳嗽、误触）不产出，避免白调一次识别
    if (!force && buffered < TARGET_RATE * MIN_SEGMENT_SECONDS) return
    if (buffered < TARGET_RATE * MIN_SEGMENT_SECONDS) {
      chunks = []
      buffered = 0
      return
    }

    const merged = new Int16Array(buffered)
    let offset = 0
    for (const chunk of chunks) {
      merged.set(chunk, offset)
      offset += chunk.length
    }
    chunks = []
    buffered = 0

    options.on_segment(encode_wav(merged, TARGET_RATE), segment_index++)
  }

  async function start() {
    if (recording) return

    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    })

    ctx = new AudioContext({ sampleRate: TARGET_RATE })
    const native_rate = ctx.sampleRate

    source = ctx.createMediaStreamSource(stream)
    processor = ctx.createScriptProcessor(4096, 1, 1)

    processor.onaudioprocess = (event) => {
      if (!recording) return
      const input = event.inputBuffer.getChannelData(0)
      const pcm = native_rate === TARGET_RATE ? input : downsample(input, native_rate, TARGET_RATE)

      const int16 = new Int16Array(pcm.length)
      for (let i = 0; i < pcm.length; i++) {
        const value = Math.max(-1, Math.min(1, pcm[i]))
        int16[i] = value < 0 ? value * 0x8000 : value * 0x7fff
      }
      chunks.push(int16)
      buffered += int16.length

      // 录满一段立即切出去，长回答不会攒到最后再传
      if (buffered >= TARGET_RATE * max_seconds) flush(true)
    }

    // 必须连到 destination 才会持续触发回调；用 0 增益避免把麦克风声音播出来
    sink = ctx.createGain()
    sink.gain.value = 0
    source.connect(processor)
    processor.connect(sink)
    sink.connect(ctx.destination)

    recording = true
    started_at = Date.now()
  }

  async function stop() {
    if (!recording) return
    recording = false

    try {
      processor?.disconnect()
      source?.disconnect()
      sink?.disconnect()
    } catch {
      // 节点已断开，忽略
    }

    stream?.getTracks().forEach((track) => track.stop())
    await ctx?.close().catch(() => undefined)

    processor = null
    source = null
    sink = null
    stream = null
    ctx = null

    flush(false) // 尾段
  }

  function dispose() {
    if (recording) {
      void stop()
      return
    }
    stream?.getTracks().forEach((track) => track.stop())
    void ctx?.close().catch(() => undefined)
    stream = null
    ctx = null
    chunks = []
    buffered = 0
  }

  return {
    start,
    stop,
    dispose,
    is_recording: () => recording,
    seconds: () => (recording ? Math.floor((Date.now() - started_at) / 1000) : 0),
  }
}
