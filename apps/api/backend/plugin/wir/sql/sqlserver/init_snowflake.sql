INSERT INTO sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
VALUES (2049629108299000110, N'项目管理', 'Project', '/project', 2, 'fe:folder', 0, NULL, 1, 1, '', NULL, NULL, GETDATE(), NULL);

INSERT INTO sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
VALUES (2049629108299000101, N'WIR 台账', 'PluginWir', '/project/wir', 1, 'fe:book-open', 1, NULL, 1, 1, '', NULL, 2049629108299000110, GETDATE(), NULL);

INSERT INTO sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
VALUES
(2049629108299000102, N'查询', 'QueryWir', NULL, 0, NULL, 2, 'wir:record:list', 1, 0, '', NULL, 2049629108299000101, GETDATE(), NULL),
(2049629108299000103, N'新增', 'AddWir', NULL, 1, NULL, 2, 'wir:record:add', 1, 0, '', NULL, 2049629108299000101, GETDATE(), NULL),
(2049629108299000104, N'修改', 'EditWir', NULL, 2, NULL, 2, 'wir:record:edit', 1, 0, '', NULL, 2049629108299000101, GETDATE(), NULL),
(2049629108299000105, N'删除', 'DeleteWir', NULL, 3, NULL, 2, 'wir:record:del', 1, 0, '', NULL, 2049629108299000101, GETDATE(), NULL),
(2049629108299000106, N'新增类型', 'AddWirType', NULL, 4, NULL, 2, 'wir:type:add', 1, 0, '', NULL, 2049629108299000101, GETDATE(), NULL),
(2049629108299000107, N'修改类型', 'EditWirType', NULL, 5, NULL, 2, 'wir:type:edit', 1, 0, '', NULL, 2049629108299000101, GETDATE(), NULL),
(2049629108299000108, N'删除类型', 'DeleteWirType', NULL, 6, NULL, 2, 'wir:type:del', 1, 0, '', NULL, 2049629108299000101, GETDATE(), NULL),
(2049629108299000109, N'导入', 'ImportWir', null, 7, null, 2, 'wir:import', 1, 0, '', null, 2049629108299000101, GETDATE(), null),
(2049629108299000111, N'导出', 'ExportWirRecord', null, 8, null, 2, 'wir:export', 1, 0, '', null, 2049629108299000101, GETDATE(), null);
