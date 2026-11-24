INSERT INTO sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
VALUES (2049629108299000201, N'材料', 'PluginPmMaterial', '/project/pm/materials', 2, 'fe:box', 1, NULL, 1, 1, '', NULL, 2049629108299000110, GETDATE(), NULL);

INSERT INTO sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
VALUES
(2049629108299000202, N'查询', 'QueryPmMaterial', NULL, 0, NULL, 2, 'pm:material:list', 1, 0, '', NULL, 2049629108299000201, GETDATE(), NULL),
(2049629108299000203, N'新增', 'AddPmMaterial', NULL, 1, NULL, 2, 'pm:material:add', 1, 0, '', NULL, 2049629108299000201, GETDATE(), NULL),
(2049629108299000204, N'修改', 'EditPmMaterial', NULL, 2, NULL, 2, 'pm:material:edit', 1, 0, '', NULL, 2049629108299000201, GETDATE(), NULL),
(2049629108299000205, N'删除', 'DeletePmMaterial', NULL, 3, NULL, 2, 'pm:material:del', 1, 0, '', NULL, 2049629108299000201, GETDATE(), NULL);
