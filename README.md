# wordpress-to-mxspace

用于将 Wordpress 的数据迁移到 Mix Space。

## 使用方法
1. 下载本仓库
2. 修改 `main.py` 中的 `file_path` 为你的 wordpress 导出数据 xml 文件路径
3. 修改 `main.py` 中的 `migrate_to_notes_func` 中的逻辑
4. 运行 `main.py`，获得 bson 文件，同时输出 `output.json` 可用于检查结构是否正确
5. 在 Mix Space 后台-维护-备份 中导出数据
6. 打开压缩包，使用 `output` 中的 bson 文件覆盖 `mx-space` 目录下的同名文件，关闭压缩包
7. 使用 [上传恢复] 功能将修改后的数据压缩包