delete from sys_menu where name in ('QueryPmMaterial', 'AddPmMaterial', 'EditPmMaterial', 'DeletePmMaterial', 'ImportPmMaterial', 'ExportPmMaterial');
delete from sys_menu where name = 'PluginPmMaterial';
drop table if exists pm_material;
select setval(pg_get_serial_sequence('sys_menu', 'id'), coalesce(max(id), 0) + 1, true) from sys_menu;
