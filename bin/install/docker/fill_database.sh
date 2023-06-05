export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "CREATE DATABASE opencapture_edissyum WITH template=template0 encoding='UTF8'" postgres
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "\i /var/www/html/opencapture/instance/sql/structure.sql" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "\i /var/www/html/opencapture/instance/sql/global.sql" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "\i /var/www/html/opencapture/instance/sql/data_fr.sql" "opencapture_edissyum"

docserverDefaultPath="/var/docservers/opencapture/"

export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path=REPLACE(path, '$docserverDefaultPath' , '/$docserverDefaultPath/edissyum/')" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path='/var/www/html/opencapture/custom/edissyum/bin/scripts/' WHERE docserver_id = 'SCRIPTS_PATH'" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path='/var/www/html/opencapture/custom/edissyum/bin/scripts/ai/splitter/train_data/' WHERE docserver_id = 'SPLITTER_TRAIN_PATH_FILES'" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path='/var/www/html/opencapture/custom/edissyum/bin/scripts/ai/splitter/models/' WHERE docserver_id = 'SPLITTER_AI_MODEL_PATH'" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path='/var/www/html/opencapture/custom/edissyum/bin/data/tmp/' WHERE docserver_id = 'TMP_PATH'" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path='/var/www/html/opencapture/custom/edissyum/bin/data/exported_pdfa/' WHERE docserver_id = 'SEPARATOR_OUTPUT_PDFA'" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path='/var/www/html/opencapture/custom/edissyum/bin/data/exported_pdf/' WHERE docserver_id = 'SEPARATOR_OUTPUT_PDF'" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE docservers SET path='/var/www/html/opencapture/custom/edissyum/instance/referencial/' WHERE docserver_id = 'REFERENTIALS_PATH'" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE inputs SET input_folder=REPLACE(input_folder, '/var/share/' , '/var/share/edissyum/')" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE outputs SET data = jsonb_set(data, '{options, parameters, 0, value}', '\"/var/share/edissyum/export/verifier/\"') WHERE data #>>'{options,parameters, 0, id}' = 'folder_out' AND module = 'verifier';" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE outputs SET data = jsonb_set(data, '{options, parameters, 0, value}', '\"/var/share/edissyum/entrant/verifier/\"') WHERE data #>>'{options,parameters, 0, id}' = 'folder_out' AND module = 'splitter' AND output_type_id = 'export_pdf';" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE outputs SET data = jsonb_set(data, '{options, parameters, 0, value}', '\"/var/share/edissyum/export/splitter/\"') WHERE data #>>'{options,parameters, 0, id}' = 'folder_out' AND module = 'splitter' AND output_type_id = 'export_xml';" "opencapture_edissyum"
export PGPASSWORD= && psql -Unathan -hpsql-database -p5432 -c "UPDATE configurations SET data = jsonb_set(data, '{value, batchPath}', '\"/var/www/html/opencapture/custom/edissyum/bin/data/MailCollect/\"') WHERE label = 'mailCollectGeneral';" "opencapture_edissyum"
