insert into sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
values (2049629108299000110, '项目管理', 'Project', '/project', 2, 'fe:folder', 0, null, 1, 1, '', null, null, now(), null);

insert into sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
values (2049629108299000101, 'WIR 台账', 'PluginWir', '/project/wir', 1, 'fe:book-open', 1, null, 1, 1, '', null, 2049629108299000110, now(), null);

insert into sys_menu (id, title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
values
(2049629108299000102, '查询', 'QueryWir', null, 0, null, 2, 'wir:record:list', 1, 0, '', null, 2049629108299000101, now(), null),
(2049629108299000103, '新增', 'AddWir', null, 1, null, 2, 'wir:record:add', 1, 0, '', null, 2049629108299000101, now(), null),
(2049629108299000104, '修改', 'EditWir', null, 2, null, 2, 'wir:record:edit', 1, 0, '', null, 2049629108299000101, now(), null),
(2049629108299000105, '删除', 'DeleteWir', null, 3, null, 2, 'wir:record:del', 1, 0, '', null, 2049629108299000101, now(), null),
(2049629108299000106, '新增类型', 'AddWirType', null, 4, null, 2, 'wir:type:add', 1, 0, '', null, 2049629108299000101, now(), null),
(2049629108299000107, '修改类型', 'EditWirType', null, 5, null, 2, 'wir:type:edit', 1, 0, '', null, 2049629108299000101, now(), null),
(2049629108299000108, '删除类型', 'DeleteWirType', null, 6, null, 2, 'wir:type:del', 1, 0, '', null, 2049629108299000101, now(), null),
(2049629108299000109, '导入', 'ImportWir', null, 7, null, 2, 'wir:import', 1, 0, '', null, 2049629108299000101, now(), null);
