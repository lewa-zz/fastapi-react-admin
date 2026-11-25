DELETE FROM sys_menu WHERE name IN ('QueryPmMaterial', 'AddPmMaterial', 'EditPmMaterial', 'DeletePmMaterial', 'ImportPmMaterial', 'ExportPmMaterial');
DELETE FROM sys_menu WHERE name = 'PluginPmMaterial';
DROP TABLE IF EXISTS pm_material;
