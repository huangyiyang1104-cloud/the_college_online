/**
 * 题干/选项里常带代码（Java、Python、SQL 片段），
 * 纯文本渲染会把换行和缩进压成一行，做题时很难看清。
 *
 * 这里判断"是否像代码"：必须含换行，且出现代码关键字或成对的括号/分号。
 * 命中则套等宽字体 + 保留缩进的样式块。
 */
const CODE_SIGNAL =
  /(^|\n)\s*(public|private|protected|static|class|interface|enum|def|function|func|var|let|const|import|package|#include|std::|select|update|insert|create|drop|alter)\b|;\s*(\n|$)|\{\s*(\n|$)|\}\s*(\n|$)|^\s{2,}\S/m

export function is_code_text(text: string): boolean {
  if (!text || !text.includes('\n')) return false
  return CODE_SIGNAL.test(text)
}
