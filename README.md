# report-convert

## changelogs

### 2025-02-26 by keyon

- 配置文件 `[paths]` 下添加 `public_folder`,`poppler_path`
        - public_folder: 生成的图片保存路径
        - poppler_path: poppler 路径

- 不再使用 watchdog, 因为监听文件修改 modified event 会触发多次, 处理比较麻烦

- 使用轮询的方式, 每隔 `check_interval` 时间去数据库检查数据并更新 图片

- 数据库添加字段

    ```sql
    -- 上次图片报告更新时间
    ALTER TABLE cbis.report ADD imgupdate DATETIME NULL;

    -- anareport 图片列表
    ALTER TABLE cbis.report ADD anaimglist TEXT NULL;

    -- reviewreport 图片列表
    ALTER TABLE cbis.report ADD reviewimglist TEXT NULL;
    ```
