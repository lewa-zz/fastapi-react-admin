delete from sys_menu where name in ('QueryPmMaterial', 'AddPmMaterial', 'EditPmMaterial', 'DeletePmMaterial');
delete from sys_menu where name = 'PluginPmMaterial';
drop table if exists pm_material;
