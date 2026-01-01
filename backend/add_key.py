# 追加 API_ENCRYPTION_KEY 到 .env 文件
with open('.env', 'ab') as f:
    # 写入换行和注释
    f.write(b'\n# API Key \xbc\xfc\xc3\xdc\xc5\xe4\xd6\xc3\xa3\xa8\xb9\xcc\xb6\xa8\xc3\xdc\xd4\xbf\xa3\xac\xc7\xeb\xce\xf1\xd0\xde\xb8\xc4\xa3\xa9\n')
    f.write(b'API_ENCRYPTION_KEY=6wrqhw8wkmly-T8928JLnTVzLKUlawL8M5GvXIX8xg8=\n')

print("✅ API_ENCRYPTION_KEY 已成功添加到 .env 文件")
