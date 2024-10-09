from wpconvert import convert_to_bson, convert_keys_and_values
from wpfile import move_files_and_rename
import json

def migrate_pic_func(pic_url):
    """
    用于替换图片链接，这里采用的文件命名规则是 year_month_filename
    """
    new_pic_url = pic_url
    if pic_url.startswith("https://blog.fosky.top/wp-content/uploads/"):
        path = pic_url.split("/")
        year = path[-3]
        month = path[-2]
        file_name = path[-1]
        pic_file_name = f"{year}_{month}_{file_name}"
        new_pic_url = f"https://space.local/api/v2/objects/file/{pic_file_name}"

    return new_pic_url

def migrate_to_notes_func(post_data):
    """
    用于将有密码 / 状态文章迁移为手记。
    本人使用的是 Kratos-pjax 主题，该主题的状态文章自定义字段 post_format 为 post-format-status。
    如果你只需要迁移有密码文章，可以将条件改为 post_data["password"] != None。
    """
    # return post_data["password"] != None
    return post_data["password"] != None or (
        "post_format" in post_data["custom_fields"] and post_data["custom_fields"]["post_format"] == "post-format-status"
    )

def rename_pic_file_func(year, month, file_name):
    """
    用于将图片文件名转换为 year_month_filename, 可以自行修改命名规则
    """
    return f"{year}_{month}_{file_name}"

if __name__ == "__main__":
    # 请将 file_path 替换为你的 WordPress 导出文件路径
    file_path = "foskym039sblog.WordPress.2024-10-07.xml"

    
    # result = convert_to_bson(file_path, "output", migrate_pic_func, migrate_to_notes_func)

    # # 如果你不需要检查数据，可以把后面的注释了
    # result = convert_keys_and_values(result)
    # with open("output.json", "w") as f:
    #     f.write(json.dumps(result, indent=4))

    # 扫描 uploads 文件夹，将图片文件名转换为 year_month_filename
    dir_path = "uploads"
    target_dir_path = "files"

    move_files_and_rename(dir_path, target_dir_path, rename_pic_file_func)