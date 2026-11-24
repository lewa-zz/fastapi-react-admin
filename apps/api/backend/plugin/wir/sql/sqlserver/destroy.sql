DELETE FROM sys_menu WHERE name IN ('QueryWir', 'AddWir', 'EditWir', 'DeleteWir', 'AddWirType', 'EditWirType', 'DeleteWirType', 'ImportWir');
DELETE FROM sys_menu WHERE name = 'PluginWir';
DELETE FROM sys_menu WHERE name = 'Project';
DROP TABLE IF EXISTS wir_record;
DROP TABLE IF EXISTS wir_type;
