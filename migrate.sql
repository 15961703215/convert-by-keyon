
-- 上次图片报告更新时间
ALTER TABLE cbis.report ADD imgupdate DATETIME NULL;

-- anareport 图片列表
ALTER TABLE cbis.report ADD anaimglist TEXT NULL;

-- reviewreport 图片列表
ALTER TABLE cbis.report ADD reviewimglist TEXT NULL;
