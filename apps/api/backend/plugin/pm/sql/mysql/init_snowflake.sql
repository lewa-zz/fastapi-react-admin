insert into sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
values (2049629108299000201, '材料', 'PluginPmMaterial', '/project/pm/materials', 2, 'fe:box', 1, null, 1, 1, '', null, 2049629108299000110, now(), null);

insert into sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
values
(2049629108299000202, '查询', 'QueryPmMaterial', null, 0, null, 2, 'pm:material:list', 1, 0, '', null, 2049629108299000201, now(), null),
(2049629108299000203, '新增', 'AddPmMaterial', null, 1, null, 2, 'pm:material:add', 1, 0, '', null, 2049629108299000201, now(), null),
(2049629108299000204, '修改', 'EditPmMaterial', null, 2, null, 2, 'pm:material:edit', 1, 0, '', null, 2049629108299000201, now(), null),
(2049629108299000205, '删除', 'DeletePmMaterial', null, 3, null, 2, 'pm:material:del', 1, 0, '', null, 2049629108299000201, now(), null);
