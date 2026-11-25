delete from sys_menu where name in ('QueryWir', 'AddWir', 'EditWir', 'DeleteWir', 'AddWirType', 'EditWirType', 'DeleteWirType', 'ImportWir', 'ExportWirRecord');
delete from sys_menu where name = 'PluginWir';
DELETE FROM sys_menu WHERE name = 'Project';
drop table if exists wir_record;
drop table if exists wir_type;
