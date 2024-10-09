import os

def move_files_and_rename(
    dir_path: str, 
    target_dir_path: str, 
    rename_func: callable = None
):
    if os.path.exists(target_dir_path):
        for file_name in os.listdir(target_dir_path):
            os.remove(os.path.join(target_dir_path, file_name))
    else:
        os.mkdir(target_dir_path)
        
    for year_dir in os.listdir(dir_path):
        try:
            year = int(year_dir.split("/")[-1])
        except:
            continue

        for month_dir in os.listdir(os.path.join(dir_path, year_dir)):
            for file_name in os.listdir(os.path.join(dir_path, year_dir, month_dir)):
                if "-" in file_name:
                    scale = file_name.split("-")[-1]
                    if scale == "scaled" or "x" in scale:
                        continue
                if rename_func:
                    new_file_name = rename_func(year_dir, month_dir, file_name)
                else:
                    new_file_name = f"{year_dir}_{month_dir}_{file_name}"
    
                with open(os.path.join(dir_path, year_dir, month_dir, file_name), "rb") as f:
                    with open(os.path.join(target_dir_path, new_file_name), "wb") as f2:
                        f2.write(f.read())
                        f2.close()
                    f.close()