INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'项目管理', 'Project', '/project', 2, 'fe:folder', 0, NULL, 1, 1, '', NULL, NULL, GETDATE(), NULL;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'WIR 台账', 'PluginWir', '/project/wir', 1, 'fe:book-open', 1, NULL, 1, 1, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'Project' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'查询', 'QueryWir', NULL, 0, NULL, 2, 'wir:record:list', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'新增', 'AddWir', NULL, 1, NULL, 2, 'wir:record:add', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'修改', 'EditWir', NULL, 2, NULL, 2, 'wir:record:edit', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'删除', 'DeleteWir', NULL, 3, NULL, 2, 'wir:record:del', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'新增类型', 'AddWirType', NULL, 4, NULL, 2, 'wir:type:add', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'修改类型', 'EditWirType', NULL, 5, NULL, 2, 'wir:type:edit', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'删除类型', 'DeleteWirType', NULL, 6, NULL, 2, 'wir:type:del', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'导入', 'ImportWir', NULL, 7, NULL, 2, 'wir:import', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginWir' AND deleted = 0;
