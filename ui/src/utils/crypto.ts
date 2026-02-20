/**
 * 加密工具函数
 * 用于前端密码哈希等安全操作
 */

import SHA256 from 'crypto-js/sha256'
import HmacSHA256 from 'crypto-js/hmac-sha256'

/**
 * 对密码进行 SHA256 哈希
 * 注意：这只是传输层保护，真正的密码安全由后端 bcrypt 保证
 * @param password 明文密码
 * @returns 哈希后的密码（64位十六进制字符串）
 */
export function hashPassword(password: string): string {
  if (!password) return ''
  return SHA256(password).toString()
}

/**
 * 生成随机 nonce（一次性随机数）
 * 用于防止重放攻击
 * @returns 随机字符串
 */
export function generateNonce(): string {
  return Date.now().toString(36) + Math.random().toString(36).substring(2)
}

/**
 * 生成请求签名 (HMAC-SHA256)
 * 用于防止请求篡改和重放攻击
 * @param method HTTP 方法
 * @param path 请求路径
 * @param timestamp 时间戳
 * @param nonce 随机数
 * @param body 请求体（可选）
 * @param secret 签名密钥 (session_secret)
 * @returns HMAC-SHA256 签名字符串
 */
export function generateRequestSignature(
  method: string,
  path: string,
  timestamp: number,
  nonce: string,
  body: unknown,
  secret: string
): string {
  // 计算 body 的哈希（如果有）
  let bodyHash = ''
  if (body) {
    const bodyString = typeof body === 'string' ? body : JSON.stringify(body)
    bodyHash = SHA256(bodyString).toString()
  }

  // 构建待签名数据: METHOD + PATH + TIMESTAMP + NONCE + BODY_HASH
  const payload = `${method.toUpperCase()}${path}${timestamp}${nonce}${bodyHash}`

  // 使用 HMAC-SHA256 生成签名
  return HmacSHA256(payload, secret).toString()
}

/**
 * 清理敏感数据
 * 用随机数据覆盖原值后再清空，防止内存中残留
 * @param value 要清理的字符串引用
 */
export function secureClear(value: { value: string }): void {
  // 先用随机数据覆盖
  const randomFill = Array(32)
    .fill(0)
    .map(() => Math.random().toString(36).charAt(2))
    .join('')
  value.value = randomFill
  // 再清空
  value.value = ''
}
