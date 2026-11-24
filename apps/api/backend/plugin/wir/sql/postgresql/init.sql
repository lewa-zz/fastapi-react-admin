do $$
declare
    project_menu_id bigint;
    wir_menu_id bigint;
begin
    insert into sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
    values ('项目管理', 'Project', '/project', 2, 'fe:folder', 0, null, 1, 1, '', null, null, now(), null)
    returning id into project_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
    values ('WIR 台账', 'PluginWir', '/project/wir', 1, 'fe:book-open', 1, null, 1, 1, '', null, project_menu_id, now(), null)
    returning id into wir_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
    values
    ('查询', 'QueryWir', null, 0, null, 2, 'wir:record:list', 1, 0, '', null, wir_menu_id, now(), null),
    ('新增', 'AddWir', null, 1, null, 2, 'wir:record:add', 1, 0, '', null, wir_menu_id, now(), null),
    ('修改', 'EditWir', null, 2, null, 2, 'wir:record:edit', 1, 0, '', null, wir_menu_id, now(), null),
    ('删除', 'DeleteWir', null, 3, null, 2, 'wir:record:del', 1, 0, '', null, wir_menu_id, now(), null),
    ('新增类型', 'AddWirType', null, 4, null, 2, 'wir:type:add', 1, 0, '', null, wir_menu_id, now(), null),
    ('修改类型', 'EditWirType', null, 5, null, 2, 'wir:type:edit', 1, 0, '', null, wir_menu_id, now(), null),
    ('删除类型', 'DeleteWirType', null, 6, null, 2, 'wir:type:del', 1, 0, '', null, wir_menu_id, now(), null),
    ('导入', 'ImportWir', null, 7, null, 2, 'wir:import', 1, 0, '', null, wir_menu_id, now(), null);
end $$;

select setval(pg_get_serial_sequence('sys_menu', 'id'), coalesce(max(id), 0) + 1, true) from sys_menu;
