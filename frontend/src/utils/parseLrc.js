/**
 * 解析 LRC 歌词文本 → 结构化 [{time, text}] 数组
 *
 * 支持格式:
 *   [00:12.34]歌词内容
 *   [01:05.123]歌词内容
 *   [00:12.34][00:45.67]重复时间标签
 */
export function parseLrc(lrcString) {
  if (!lrcString) return []

  const lines = lrcString.split('\n')
  const result = []
  const timeRegex = /\[(\d{2}):(\d{2})\.(\d{2,3})\]/g

  for (const line of lines) {
    const times = []
    let match

    while ((match = timeRegex.exec(line)) !== null) {
      const min = parseInt(match[1])
      const sec = parseInt(match[2])
      const ms = parseInt(match[3].padEnd(3, '0'))
      times.push(min * 60 + sec + ms / 1000)
    }

    // 去掉所有时间标签后保留纯文本
    const text = line.replace(timeRegex, '').trim()

    // 跳过空行和纯元数据行 (作词/作曲等)
    if (!text) continue
    if (/^(作词|作曲|编曲|制作|混音|录音|母带)[：:]/.test(text)) continue

    if (times.length > 0) {
      times.forEach(time => result.push({ time, text }))
    }
  }

  return result.sort((a, b) => a.time - b.time)
}
