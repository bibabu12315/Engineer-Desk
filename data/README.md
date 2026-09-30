# 数据目录

本目录存放 Engineer Desk 的全部本地数据，**请勿删除**。

## 内容

| 文件 | 说明 |
| --- | --- |
| `engineer_desk.db` | SQLite 主数据库（便签正文、Todo、标签、配置、窗口位置与外观） |
| `engineer_desk.db-wal` / `-shm` | SQLite WAL 日志文件，数据库打开时自动生成，不要单独删除 |

## 为什么放在这里

- 数据固定在工程根目录的 `data/`，与 `build/`、`dist/` 等构建产物目录完全分离；
- 执行 `build.bat` 会清空 `dist/`，但不会触碰 `data/`，因此重新打包 / 升级版本不会丢失历史数据；
- 打包后的 exe 运行时会自动向上定位到工程根目录，同样读写这里的 `data/`。

## 历史数据迁移

旧版本数据库位于 `%APPDATA%\EngineerDesk\engineer_desk.db`。
新版本**首次启动**时会自动把该库完整复制到本目录（使用 SQLite 在线备份接口，包含未落盘的 WAL 数据）。
迁移只在 `engineer_desk.db` 不存在或为空时执行一次，不会覆盖已有数据。旧库文件会保留，可自行确认无误后删除。

## 自定义位置

如需把数据放到其它目录（例如同步盘），设置环境变量后重启程序即可：

```
ENGINEERDESK_DATA_DIR=D:\SomeWhere\EngineerDeskData
```

## 备份建议

直接复制整个 `data/` 目录即可完成备份。建议在复制前先退出程序，或至少确认 `engineer_desk.db-wal` 已被合并。
