INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'材料', 'PluginPmMaterial', '/project/pm/materials', 2, 'fe:box', 1, NULL, 1, 1, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'Project' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'查询', 'QueryPmMaterial', NULL, 0, NULL, 2, 'pm:material:list', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginPmMaterial' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'新增', 'AddPmMaterial', NULL, 1, NULL, 2, 'pm:material:add', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginPmMaterial' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'修改', 'EditPmMaterial', NULL, 2, NULL, 2, 'pm:material:edit', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginPmMaterial' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'删除', 'DeletePmMaterial', NULL, 3, NULL, 2, 'pm:material:del', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginPmMaterial' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'导入', 'ImportPmMaterial', NULL, 4, NULL, 2, 'pm:material:import', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginPmMaterial' AND deleted = 0;

INSERT INTO sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
SELECT N'导出', 'ExportPmMaterial', NULL, 5, NULL, 2, 'pm:material:export', 1, 0, '', NULL, id, GETDATE(), NULL
FROM sys_menu WHERE name = 'PluginPmMaterial' AND deleted = 0;
