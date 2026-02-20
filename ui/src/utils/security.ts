/**
 * 安全工具函数
 * XSS 防护、输入清理等
 */

/**
 * 转义 HTML 特殊字符，防止 XSS
 * @param text 原始文本
 * @returns 转义后的文本
 */
export function escapeHtml(text: string): string {
  if (!text) return ''
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * 清理用户输入，移除危险字符
 * @param input 用户输入
 * @returns 清理后的输入
 */
export function sanitizeInput(input: string): string {
  if (!input) return ''
  // 移除可能的脚本标签和事件处理器
  return input
    .replace(/<script[^>]*>.*?<\/script>/gi, '')
    .replace(/<[^>]+\s+on\w+\s*=\s*["'][^"']*["'][^>]*>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/data:text\/html/gi, '')
    .trim()
}

/**
 * 验证用户名格式
 * @param username 用户名
 * @returns 是否有效
 */
export function validateUsername(username: string): boolean {
  // 只允许字母、数字、下划线，长度 3-32
  const pattern = /^[a-zA-Z0-9_]{3,32}$/
  return pattern.test(username)
}

/**
 * 验证邮箱格式
 * @param email 邮箱
 * @returns 是否有效
 */
export function validateEmail(email: string): boolean {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return pattern.test(email)
}

/**
 * 验证密码强度
 * @param password 密码
 * @returns 验证结果
 */
export function validatePassword(password: string): {
  valid: boolean
  message: string
} {
  if (!password || password.length < 6) {
    return { valid: false, message: '密码长度至少 6 位' }
  }
  if (password.length > 64) {
    return { valid: false, message: '密码长度不能超过 64 位' }
  }
  // 检查是否包含至少两种字符类型
  const hasLetter = /[a-zA-Z]/.test(password)
  const hasNumber = /\d/.test(password)
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password)

  const typeCount = [hasLetter, hasNumber, hasSpecial].filter(Boolean).length
  if (typeCount < 2) {
    return {
      valid: false,
      message: '密码需包含字母、数字或特殊字符中的至少两种',
    }
  }
  return { valid: true, message: '' }
}

/**
 * 检查是否为纯文本（无 HTML）
 * @param text 文本
 * @returns 是否安全
 */
export function isPlainText(text: string): boolean {
  return !/[<>]/.test(text)
}

/**
 * 生成 CSRF Token
 * 用于防止跨站请求伪造
 * @returns 随机 token
 */
export function generateCSRFToken(): string {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('')
}
