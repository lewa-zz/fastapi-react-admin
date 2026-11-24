do $$
declare
    project_menu_id bigint;
    pm_material_menu_id bigint;
begin
    select id into project_menu_id from sys_menu where name = 'Project' and deleted = 0 limit 1;

    insert into sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
    values ('材料', 'PluginPmMaterial', '/project/pm/materials', 2, 'fe:box', 1, null, 1, 1, '', null, project_menu_id, now(), null)
    returning id into pm_material_menu_id;

    insert into sys_menu (title, name, path, sort, icon, type, perms, status, display, link, remark, parent_id, created_time, updated_time)
    values
    ('查询', 'QueryPmMaterial', null, 0, null, 2, 'pm:material:list', 1, 0, '', null, pm_material_menu_id, now(), null),
    ('新增', 'AddPmMaterial', null, 1, null, 2, 'pm:material:add', 1, 0, '', null, pm_material_menu_id, now(), null),
    ('修改', 'EditPmMaterial', null, 2, null, 2, 'pm:material:edit', 1, 0, '', null, pm_material_menu_id, now(), null),
    ('删除', 'DeletePmMaterial', null, 3, null, 2, 'pm:material:del', 1, 0, '', null, pm_material_menu_id, now(), null);
end $$;

select setval(pg_get_serial_sequence('sys_menu', 'id'), coalesce(max(id), 0) + 1, true) from sys_menu;
