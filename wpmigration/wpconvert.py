from .wpparser import wpparse
import os
import re
import json
import bson
import collections
from markdownify import markdownify
from urllib.parse import unquote
from datetime import datetime
from bson import ObjectId
from typing import Union

def convert_keys_and_values(data):
    """
    将字典中的键和值转换为字符串，以便序列化为 JSON
    """
    if isinstance(data, dict):
        return {str(key): convert_keys_and_values(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_keys_and_values(element) for element in data]
    elif isinstance(data, bytes):
        return data.decode('utf-8')
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data

def format_datetime(date: Union[str, datetime]):
    """
    将日期字符串转换为 datetime 对象
    """
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    
    return date
    
def json_array_to_bson(json_array: list):
    """
    将 JSON 数组转换为 BSON 格式
    """
    return b''.join(bson.encode(json_obj) for json_obj in json_array)

def convert_to_bson(
    wp_xml_file_path: str, 
    output_dir: str = "output",
    migrate_pic_func: callable = None,
    migrate_to_notes_func: callable = None
) -> dict:
    """
    将 WordPress 导出的 XML 文件转换为 BSON 格式
    """
    result = wpparse(wp_xml_file_path)
    result = convert_keys_and_values(result)
    tables = _process_tablepress_tables(result)
    _process_content(result, tables, migrate_pic_func)
    migrations = _create_migrations(result)
    _process_posts(result, migrations)
    _process_pages(result, migrations)
    _process_comments(result, migrations)
    _link_comments(migrations)
    _assign_comment_keys(migrations)
    _migrate_posts_to_notes(migrations, migrate_to_notes_func)
    _save_migrations_to_bson(migrations, output_dir)
    return migrations

def _process_tablepress_tables(result):
    """
    Tablepress 插件的表格导出
    """
    tables = []
    if "tablepress_table" in result["items"]:
        for table in result["items"]["tablepress_table"]:
            table_data = json.loads(table["content"])
            table_header, table_rows = table_data[0], table_data[1:]
            table_markdown = " | " + " | ".join(table_header) + " |\n"
            table_markdown += " | " + " | ".join(["---"] * len(table_header)) + " |\n"
            table_markdown += "\n".join(" | " + " | ".join(row) + " |" for row in table_rows)
            tables.append({
                "id": table["postmeta"]["_tablepress_export_table_id"],
                "content": table_markdown,
            })
        result["items"].pop("tablepress_table")
    return tables

def _process_content(result: dict, tables: list, migrate_pic_func: callable = None):
    for _type in ['post', 'page']:
        if _type in result["items"]:
            for item in result["items"][_type]:
                if item["content"]:
                    item["content"] = markdownify(item["content"])
                    if migrate_pic_func is not None:
                        pattern = re.compile(r"!\[.*?\]\((.*?)\)")
                        pictures = pattern.findall(item["content"])
                        for pic_url in pictures:
                            new_pic_url = migrate_pic_func(pic_url)
                            item["content"] = item["content"].replace(pic_url, new_pic_url)

                    for table in tables:
                        item["content"] = item["content"].replace(f"\[table id\={table['id']} /]", table["content"])

def _create_migrations(result):
    created_date = datetime.now()
    migrations = {
        "categories": [
            {
                "_id": ObjectId(),
                "name": category["name"],
                "type": 0,
                "slug": category["nicename"],
                "created": created_date
            } for category in result["categories"]
        ],
        "comments": [],
        "posts": [],
        "pages": [],
        "notes": []
    }
    return migrations

def _process_posts(result, migrations):
    for post in result["items"]["post"]:
        category_id = next((category["_id"] for category in migrations["categories"] if category["slug"] == post["categories"][0]), None)
        data = {
            "_id": ObjectId(),
            "created": format_datetime(post["post_date"]),
            "commentsIndex": 0,
            "allowComment": post["comment_status"] == "open",
            "title": post["title"],
            "text": post["content"],
            "images": [],
            "modified": format_datetime(post["post_modified"]),
            "slug": post["post_name"],
            "summary": post["excerpt"],
            "categoryId": category_id,
            "copyright": True,
            "tags": [unquote(tag) for tag in post["tags"]],
            "count": {
                "read": int(post["postmeta"].get("views", 0)),
                "like": int(post["postmeta"].get("love", 0))
            },
            "pin": None,
            "pinOrder": 0,
            "related": [],
            "meta": "null",
            "original": {
                "password": post["post_password"],
                "postmeta": post["postmeta"],
                "custom_fields": post["custom_fields"],
            }
        }
        migrations["posts"].append(data)

def _process_pages(result, migrations):
    for index, page in enumerate(result["items"]["page"]):
        data = {
            "_id": ObjectId(),
            "created": format_datetime(page["post_date"]),
            "commentsIndex": 0,
            "allowComment": page["comment_status"] == "open",
            "title": page["title"],
            "text": page["content"],
            "images": [],
            "modified": format_datetime(page["post_modified"]),
            "slug": page["post_name"],
            "subtitle": "",
            "order": index,
        }
        migrations["pages"].append(data)

def _process_comments(result, migrations):
    comment_ref_type_list = ['post', 'page']
    for _type in comment_ref_type_list:
        if _type in result["items"]:
            for item in result["items"][_type]:
                ref_id = next((ref["_id"] for ref in migrations["posts" if _type == 'post' else 'pages'] if ref["slug"] == item["post_name"]), None)
                for comment in item["comments"]:
                    comment["content"] = markdownify(comment["content"])
                    comment["content"] = comment["content"].replace("\\", "")
                    data = {
                        "_id": ObjectId(),
                        "ref": ref_id,
                        "refType": "posts" if _type == 'post' else 'pages',
                        "author": comment["author"],
                        "mail": comment["author_email"],
                        "url": comment["author_url"],
                        "text": comment["content"],
                        "state": 2 if comment["approved"] == "trash" else 1,
                        "children": [],
                        "commentIndex": 0,
                        "key": "",
                        "ip": comment["author_ip"],
                        "agent": "",
                        "pin": False,
                        "isWhispers": False,
                        "created": format_datetime(comment["date"]),
                        "original": {
                            "id": comment["id"],
                            "parent_id": comment["parent"]
                        }
                    }
                    migrations["comments"].append(data)

def _link_comments(migrations):
    for comment in migrations["comments"]:
        if comment["original"]["parent_id"] != "0":
            parent_comment = next((pc for pc in migrations["comments"] if pc["original"]["id"] == comment["original"]["parent_id"]), None)
            if parent_comment:
                parent_comment["children"].append(comment["_id"])
                comment['parent'] = parent_comment["_id"]
    for comment in migrations["comments"]:
        comment.pop("original")

def _assign_comment_keys(migrations):
    for comment in migrations["comments"]:
        ref = migrations["posts"] if comment["refType"] == "posts" else migrations["pages"]
        for item in ref:
            if item["_id"] == comment["ref"]:
                if "parent" not in comment:
                    item["commentsIndex"] = item.get("commentsIndex", 0) + 1
                    comment["commentIndex"] = item["commentsIndex"]
                    comment["key"] = f"#{comment['commentIndex']}"
                else:
                    parent_comment = next((pc for pc in migrations["comments"] if pc["_id"] == comment["parent"]), None)
                    if parent_comment:
                        parent_comment["commentsIndex"] = parent_comment.get("commentsIndex", 0) + 1
                        comment["commentIndex"] = parent_comment["commentsIndex"]
                        comment["key"] = f"{parent_comment['key']}#{comment['commentIndex']}"

def _migrate_posts_to_notes(migrations, migrate_to_notes_func):
    i = 0
    for post in migrations["posts"]:
        original = post.pop("original")
        if migrate_to_notes_func and migrate_to_notes_func(original):
            i += 1
            data = {
                "_id": post["_id"],
                "created": post["created"],
                "commentsIndex": 0,
                "allowComment": post["allowComment"],
                "title": post["title"],
                "text": post["text"],
                "images": [],
                "modified": post["modified"],
                "hide": original["password"] is not None,
                "password": original["password"],
                "publicAt": None,
                "mood": "",
                "weather": "",
                "bookmark": False,
                "coordinates": None,
                "location": "",
                "count": post["count"],
                "nid": i
            }
            migrations["notes"].append(data)
            for comment in migrations["comments"]:
                if comment["ref"] == post["_id"]:
                    comment["refType"] = "notes"

def _save_migrations_to_bson(migrations, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    for key, value in migrations.items():
        file_path = os.path.join(output_dir, f"{key}.bson")
        with open(file_path, "wb") as f:
            f.write(json_array_to_bson(value))