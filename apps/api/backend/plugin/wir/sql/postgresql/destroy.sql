delete from sys_menu where name in ('QueryWir', 'AddWir', 'EditWir', 'DeleteWir', 'AddWirType', 'EditWirType', 'DeleteWirType', 'ImportWir');
delete from sys_menu where name = 'PluginWir';
DELETE FROM sys_menu WHERE name = 'Project';
drop table if exists wir_record;
drop table if exists wir_type;
select setval(pg_get_serial_sequence('sys_menu', 'id'), coalesce(max(id), 0) + 1, true) from sys_menu;
