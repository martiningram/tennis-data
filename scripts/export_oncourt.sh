oncourt_dir='/home/martin/.PlayOnLinux/wineprefix/OnCourtFeb/drive_c/Program Files/OnCourt/'
mdb_file="$oncourt_dir/OnCourt.mdb"
target_dir="/home/martin/projects/tennis-data/data/oncourt/"

for cur_table in $(mdb-tables "$mdb_file"); do
  echo "Exporting $cur_table."
  target_file="$target_dir"/"$cur_table".csv
  mdb-export "$mdb_file" "$cur_table" > "$target_file"
done
