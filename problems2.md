# 配图显示故障分析与修复方案（第二轮）

## 故障现象

配图流程现在能跑通了（上一轮修复生效），正文中的占位符已被替换为COS URL，但**浏览器访问这些URL时返回 `AccessDenied`**，图片无法显示。

用户在浏览器中打开图片地址，看到：
```xml
<Error>
  <Code>AccessDenied</Code>
  <Message>Access Denied.</Message>
  <Resource>/article-images/c3c45885/image_2.png</Resource>
</Error>
```

---

## 根因分析

### 🔴 核心问题：COS 存储桶默认私有读写，上传的文件未设置公共读权限

**位置**: `backend/app/utils/cos_uploader.py` 第369-381行 `_upload_to_cos()` 中的 `_sync_upload()`

**问题详解**:

腾讯云 COS 存储桶有两种访问权限模式：
1. **私有读写**（默认）：所有对象需要签名才能访问
2. **公有读私有写**：对象可通过URL直接访问

当前代码 `client.put_object(Bucket=..., Body=..., Key=...)` 上传文件时，**没有指定对象的 ACL**，因此对象继承了存储桶的默认权限——私有读写。

结果就是：
- 文件确实成功上传到了 COS（后端日志显示上传成功）
- 生成的 URL 格式正确：`https://tecent-cos-1-1401204720.cos.ap-guangzhou.myqcloud.com/article-images/c3c45885/image_2.png`
- 但浏览器直接访问这个 URL 时，COS 服务端检查到该对象是私有的、请求没有签名，返回 `AccessDenied`

**补充说明**：你的 `.env` 中 COS 配置是完整的（SecretId、SecretKey、Bucket、Region 都有），配置本身没有问题。问题出在上传代码没有设置对象的访问权限。

---

## 解决方案

有 **3 种方案**，推荐方案 A（代码层面修复，最稳妥）：

### 方案 A（推荐）：上传时设置对象 ACL 为 public-read

在 `_sync_upload()` 中给 `put_object` 增加参数 `ACL='public-read'`，使上传的每个图片对象都可以被公开访问。

**优点**：
- 只影响上传的图片对象，不影响存储桶中其他对象
- 不需要去腾讯云控制台修改存储桶全局权限
- 代码可控，未来可以按需调整为更细粒度的权限

**改动**：只需修改 `cos_uploader.py` 中的 `put_object` 调用，增加一行参数

### 方案 B：在腾讯云控制台将存储桶设为"公有读私有写"

在腾讯云 COS 控制台 → 存储桶列表 → `tecent-cos-1-1401204720` → 权限管理 → 存储桶访问权限 → 改为"公有读私有写"。

**优点**：不需要改代码
**缺点**：影响存储桶中所有对象（包括未来可能需要私有的对象），安全性较差

### 方案 C：生成预签名 URL（不推荐）

使用 COS SDK 生成带签名的临时访问 URL（有效期如 1 小时），替代当前的直接 URL。

**优点**：最安全
**缺点**：URL 会过期，文章中的图片链接一段时间后失效；且需要大幅修改代码

---

## 推荐方案 A 的具体改动

### 修改 `backend/app/utils/cos_uploader.py`

在 `_sync_upload()` 内部，给 `put_object` 增加 `ACL='public-read'` 参数：

```python
def _sync_upload():
    config = CosConfig(
        Region=self.region,
        SecretId=self.secret_id,
        SecretKey=self.secret_key,
    )
    client = CosS3Client(config)
    with open(file_path, "rb") as fp:
        response = client.put_object(
            Bucket=self.bucket,
            Body=fp,
            Key=cos_key,
            ACL='public-read',  # ← 新增：设置对象为公开可读
        )
    return response
```

**仅此一处改动，修改量极小。**

---

## 验证步骤

1. 重启后端服务
2. 创建新任务，走完整个流程
3. 在最终文章中检查图片 URL
4. 在浏览器中直接打开图片 URL，应能正常显示图片
5. 在前端页面中确认图片正常渲染

---

## 已上传旧图片的处理

方案 A 只影响**新上传**的图片。之前已经上传的图片仍然是私有的，需要处理：

1. **最简方案**：重新生成一篇文章即可，新文章的图片会使用 public-read 权限
2. **批量修复旧图片**：在腾讯云控制台 → 存储桶 → 文件列表 → 批量选中 `article-images/` 目录下的文件 → 修改权限为公有读

---

## 总结

| 项目 | 说明 |
|------|------|
| 根因 | COS put_object 未设置 ACL，对象默认私有，浏览器直接访问被拒绝 |
| 影响 | 所有上传到 COS 的图片无法在浏览器中直接访问 |
| 修复 | put_object 增加 `ACL='public-read'` 参数 |
| 改动量 | 1 行代码 |
| 风险 | 无，仅让图片对象可公开读取 |
