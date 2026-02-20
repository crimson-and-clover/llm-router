/**
 * 加密工具函数
 * 用于前端密码哈希等安全操作
 */

import SHA256 from 'crypto-js/sha256'

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
 * 生成请求签名
 * 可用于关键操作的额外验证
 * @param data 要签名的数据
 * @param timestamp 时间戳
 * @param nonce 随机数
 * @returns 签名字符串
 */
export function generateRequestSignature(
  data: Record<string, any>,
  timestamp: number,
  nonce: string
): string {
  // 按字母顺序排序并序列化
  const sortedData = Object.keys(data)
    .sort()
    .reduce((acc, key) => {
      acc[key] = data[key]
      return acc
    }, {} as Record<string, any>)

  const payload = JSON.stringify(sortedData) + timestamp + nonce
  return SHA256(payload).toString()
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
