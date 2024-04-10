ALTER TABLE hunt_output_plugins_states
ADD COLUMN plugin_args_any MEDIUMBLOB DEFAULT NULL AFTER plugin_args;
