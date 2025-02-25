from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

def encode(key, plaintext):
    # 将输入的字符串key转换为bytes
    key = key.encode('utf-8')
    # 确保密钥长度为16字节（即128-bit），这里假设输入的密钥长度正确
    if len(key) != 16:
        raise ValueError("Key must be 16 bytes long.")
    # 创建一个新的AES cipher对象
    cipher = AES.new(key, AES.MODE_ECB)
    # 加密前对明文进行utf-8编码，并使用PKCS7规范填充至块大小的倍数
    padded_plaintext = pad(plaintext.encode('utf-8'), AES.block_size)
    # 执行加密操作
    ciphertext = cipher.encrypt(padded_plaintext)
    # 返回加密后的数据的base64编码字符串表示形式
    return base64.b64encode(ciphertext).decode('utf-8')