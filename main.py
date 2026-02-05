from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import GetPosts, NewPost, EditPost
from urllib.parse import urlparse
import frontmatter
import time
import os
from hashlib import md5, sha1
import json
import markdown
import re
import urllib.parse
import requests
import mimetypes

config_file_txt = ""

if((os.path.exists(os.path.join(os.getcwd(), "diy_config.txt")) == True)):
    config_file_txt = os.path.join(os.getcwd(), "diy_config.txt")
else:
    config_file_txt = os.path.join(os.getcwd(), "config.txt")

config_info = {}

# 每一篇文章暂停的时间，避免请求过快被服务器拒绝
SLEEP_TIME_BETWEEN_POSTS = 30 #秒

with open (config_file_txt, 'rb') as f:
    config_info = json.loads(f.read())


username = config_info["USERNAME"]
password = config_info["PASSWORD"]
xmlrpc_php = config_info["XMLRPC_PHP"]
# 处理本地图片上传的配置
image_hosting_url = config_info["IMAGE_HOSTING_URL"]
image_hosting_secret_token = config_info["IMAGE_HOSTING_SECRET_TOKEN"]

try:
    if(os.environ["USERNAME"]):
        username = os.environ["USERNAME"]

    if(os.environ["PASSWORD"]):
        password = os.environ["PASSWORD"]

    if(os.environ["XMLRPC_PHP"]):
        xmlrpc_php = os.environ["XMLRPC_PHP"]
    # 将本地url上传到图床
    if(os.environ["IMAGE_HOSTING_URL"]):
        image_hosting_url = os.environ["IMAGE_HOSTING_URL"]
    if(os.environ["IMAGE_HOSTING_SECRET_TOKEN"]):
        image_hosting_secret_token = os.environ["IMAGE_HOSTING_SECRET_TOKEN"]
except:
    print("无法获取github的secrets配置信息,开始使用本地变量")


url_info = urlparse(xmlrpc_php)

domain_name = url_info.netloc

wp = Client(xmlrpc_php, username, password)

def handle_local_markdown_image(md_path, content):
    # 第一步：content为markdown格式，从content里查找所有的本地图片链接，本地图片不以http开头
    local_image_link_list = []
    # markdown image: ![alt](path "title")
    for match in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content):
        link = match.strip().split()[0]
        if link and (link.startswith("http") == False):
            local_image_link_list.append(link)
    # html image: <img src="path">
    for match in re.findall(r'<img[^>]*src=[\'"]([^\'"]+)[\'"]', content):
        link = match.strip()
        if link and (link.startswith("http") == False):
            local_image_link_list.append(link)
    # 去重并保持顺序，后续步骤使用
    seen = set()
    local_image_link_list = [x for x in local_image_link_list if (x in seen) == False and (seen.add(x) or True)]

    # 将本地图片链接处理为绝对路径，方便后续上传
    local_image_abs_path_list = []
    local_image_link_abs_pairs = []
    md_dir = os.path.dirname(os.path.abspath(md_path))
    for link in local_image_link_list:
        # 绝对路径不处理，相对路径基于 md_path 所在目录
        if os.path.isabs(link):
            abs_path = link
        else:
            abs_path = os.path.normpath(os.path.join(md_dir, link))
        local_image_abs_path_list.append(abs_path)
        local_image_link_abs_pairs.append((link, abs_path))
    print("local_image_abs_path_list==>>", local_image_abs_path_list)

    # 第二步：读取本地图片信息，可以通过md_path获取图片的绝对路径进行处理，通过requests post方式往image_hosting_url发送，每次一张，依次上传，可以参考的js实现，用python的requests实现
    local_image_path_to_http_url = {}
    for (image_link, image_abs_path) in local_image_link_abs_pairs:
        if os.path.exists(image_abs_path) == False:
            print("图片不存在，跳过==>>", image_abs_path)
            continue
        try:
            with open(image_abs_path, 'rb') as f:
                mime_type = mimetypes.guess_type(image_abs_path)[0] or "application/octet-stream"
                file_name = os.path.basename(image_abs_path)
                files = {"file": (file_name, f, mime_type)}
                data = {}
                if image_hosting_secret_token:
                    data["secret_token"] = image_hosting_secret_token
                res = requests.post(image_hosting_url, files=files, data=data, timeout=30)
                # 打印出的值为 upload_res==>> https://cdn.fangyuanxiaozhan.com/assets/1766384328413NB766Xri.png
                print("upload_res==>>", res.text)
                local_image_path_to_http_url[image_link] = res.text
        except Exception as e:
            print("图片上传失败，跳过==>>", image_abs_path, str(e))

    # 第三步：获取图片上传后的链接，替换content中的本地链接为上传后的链接，对于上传失败的图片，跳过替换, 将local_image_path_to_http_url里面的键值对进行遍历，然后替换content中的链接
    for local_image_link, http_url in local_image_path_to_http_url.items():
        if http_url:
            content = content.replace(local_image_link, http_url)

    # 第四步：返回处理后的content
    return content

# 获取已发布文章id列表
def get_posts():
    print(time.strftime('%Y-%m-%d-%H-%M-%S')+"开始从服务器获取文章列表...")
    posts = wp.call(GetPosts({'post_type': 'post', 'number': 1000000000}))
    post_link_id_list = []
    for post in posts:
        post_link_id_list.append({
            "id": post.id,
            "link": post.link
        })
    print(post_link_id_list)
    print(len(post_link_id_list))
    return post_link_id_list

# 创建post对象
def create_post_obj(title, content, link, post_status, terms_names_post_tag, terms_names_category):
    post_obj = WordPressPost()
    post_obj.title = title
    post_obj.content = content
    post_obj.link = link
    post_obj.post_status = post_status
    post_obj.comment_status = "open"
    print(post_obj.link)
    post_obj.terms_names = {
        #文章所属标签，没有则自动创建
        'post_tag': terms_names_post_tag,
         #文章所属分类，没有则自动创建
        'category': terms_names_category
    }

    return post_obj



# 新建文章
def new_post(title, content, link, post_status, terms_names_post_tag, terms_names_category):

    post_obj = create_post_obj(
        title = link, 
        content = content, 
        link = link, 
        post_status = post_status, 
        terms_names_post_tag = terms_names_post_tag, 
        terms_names_category = terms_names_category)
    # 先获取id
    id = wp.call(NewPost(post_obj))
    # 再通过EditPost更新信息
    edit_post(id, title, 
        content, 
        link, 
        post_status, 
        terms_names_post_tag, 
        terms_names_category)


# 更新文章
def edit_post(id, title, content, link, post_status, terms_names_post_tag, terms_names_category):
    post_obj = create_post_obj(
        title, 
        content, 
        link, 
        post_status, 
        terms_names_post_tag, 
        terms_names_category)
    res = wp.call(EditPost(id, post_obj))
    print(res)

# 获取markdown文件中的内容
def read_md(file_path):
    content = ""
    metadata = {}
    with open(file_path) as f:
        post = frontmatter.load(f)
        content = post.content
        metadata = post.metadata
        print("==>>", post.content)
        print("===>>", post.metadata)
    return (content, metadata)

# 获取特定目录的markdown文件列表
def get_md_list(dir_path):
    md_list = []
    dirs = os.listdir(dir_path)
    for i in dirs:
        if os.path.splitext(i)[1] == ".md":   
            md_list.append(os.path.join(dir_path, i))
    print(md_list)
    return md_list

# 计算sha1
def get_sha1(filename):
    sha1_obj = sha1()
    with open(filename, 'rb') as f:
        sha1_obj.update(f.read())
    result = sha1_obj.hexdigest()
    print(result)
    return result

# 将字典写入文件
def write_dic_info_to_file(dic_info, file):
    dic_info_str = json.dumps(dic_info)   
    file = open(file, 'w')  
    file.write(dic_info_str)  
    file.close()
    return True

# 将文件读取为字典格式
def read_dic_from_file(file):
    file_byte = open(file, 'r') 
    file_info = file_byte.read()
    dic = json.loads(file_info)   
    file_byte.close()
    return dic 

# 获取md_sha1_dic

def get_md_sha1_dic(file):
    result = {}
    if(os.path.exists(file) == True):
        result = read_dic_from_file(file)
    else:
        write_dic_info_to_file({}, file)
    return result

# 重建md_sha1_dic,将结果写入.md_sha1
def rebuild_md_sha1_dic(file, md_dir):
    md_sha1_dic = {}

    md_list = get_md_list(md_dir)

    for md in md_list:
        key = os.path.basename(md).split(".")[0]
        value = get_sha1(md)
        md_sha1_dic[key] = {
            "hash_value": value,
            "file_name": key,
            "encode_file_name": urllib.parse.quote(key, safe='').lower()
        }



    md_sha1_dic["update_time"] =  time.strftime('%Y-%m-%d-%H-%M-%S')
    write_dic_info_to_file(md_sha1_dic, file)

def rebuild_md_sha1_dic_for_md_file(file, md_file_path):
    md_sha1_dic = get_md_sha1_dic(file)

    key = os.path.basename(md_file_path).split(".")[0]
    value = get_sha1(md_file_path)
    md_sha1_dic[key] = {
        "hash_value": value,
        "file_name": key,
        "encode_file_name": urllib.parse.quote(key, safe='').lower()
    }

    md_sha1_dic["update_time"] =  time.strftime('%Y-%m-%d-%H-%M-%S')
    write_dic_info_to_file(md_sha1_dic, file)

def post_link_id_list_2_link_id_dic(post_link_id_list):
    link_id_dic = {}
    for post in post_link_id_list:
        link_id_dic[post["link"]] = post["id"]
    return link_id_dic


def href_info(link):
    return "<br/><br/><br/>\n\n\n\n## 本文永久更新地址: \n[" + link + "](" + link + ")"

# 在README.md中插入信息文章索引信息，更容易获取google的收录
def insert_index_info_in_readme():
    # 获取_posts下所有markdown文件
    md_list = get_md_list(os.path.join(os.getcwd(), "_posts"))
    # 生成插入列表
    insert_info = ""
    md_list.sort(reverse=True)
    # 读取md_list中的文件标题
    for md in md_list:
        (content, metadata) = read_md(md)
        title = metadata.get("title", "")
        insert_info = insert_info + "[" + title +"](" + "https://"+domain_name + "/p/" + os.path.basename(md).split(".")[0] +"/" + ")\n\n"
    # 替换 ---start--- 到 ---end--- 之间的内容

    insert_info = "---start---\n## 目录(" + time.strftime('%Y年%m月%d日') + "更新)" +"\n" + insert_info + "---end---"

    # 获取README.md内容
    with open (os.path.join(os.getcwd(), "README.md"), 'r', encoding='utf-8') as f:
        readme_md_content = f.read()

    print(insert_info)

    new_readme_md_content = re.sub(r'---start---(.|\n)*---end---', insert_info, readme_md_content)

    with open (os.path.join(os.getcwd(), "README.md"), 'w', encoding='utf-8') as f:
        f.write(new_readme_md_content)

    print("==new_readme_md_content==>>", new_readme_md_content)

    return True

def main():
    # 1. 获取网站数据库中已有的文章列表
    post_link_id_list = get_posts()
    print(post_link_id_list)
    link_id_dic = post_link_id_list_2_link_id_dic(post_link_id_list)
    print(link_id_dic)
    # 2. 获取md_sha1_dic
    # 查看目录下是否存在md_sha1.txt,如果存在则读取内容；
    # 如果不存在则创建md_sha1.txt,内容初始化为{}，并读取其中的内容；
    # 将读取的字典内容变量名，设置为 md_sha1_dic
    # md_sha1_dic = get_md_sha1_dic(os.path.join(os.getcwd(), ".md_sha1"))

    # 3. 开始同步
    # 读取_posts目录中的md文件列表
    md_list = get_md_list(os.path.join(os.getcwd(), "_posts"))

    for md_index, md in enumerate(md_list):
        print(f"同步进度: {md_index+1}/{len(md_list)} 正在同步第 {md_index+1} 篇文章==>> 总共 {len(md_list)} 篇文章")
        md_sha1_dic = get_md_sha1_dic(os.path.join(os.getcwd(), ".md_sha1"))
        # 计算md文件的sha1值，并与md_sha1_dic做对比
        sha1_key = os.path.basename(md).split(".")[0]
        sha1_value = get_sha1(md)
        # 如果sha1与md_sha1_dic中记录的相同，则打印：XX文件无需同步;
        if((sha1_key in md_sha1_dic.keys()) and ("hash_value" in md_sha1_dic[sha1_key]) and (sha1_value == md_sha1_dic[sha1_key]["hash_value"])):
            print(md+"无需同步")
        # 如果sha1与md_sha1_dic中记录的不同，则开始同步
        else:
            # 读取md文件信息
            print(md+"开始同步==")
            (content, metadata) = read_md(md)
            # 获取title
            title = metadata.get("title", "")
            terms_names_post_tag = metadata.get("tags",  domain_name)
            terms_names_category = metadata.get("categories", domain_name)
            post_status = "publish"
            link = urllib.parse.quote(sha1_key , safe='').lower() 
            # 添加函数处理图片, 如果image_hosting_url存在，则调用handle_local_markdown_image函数处理content
            if(image_hosting_url):
                content = handle_local_markdown_image(md, content)
            content = markdown.markdown(content + href_info("https://"+domain_name+"/p/"+link+"/"), extensions=['tables', 'fenced_code'])
            # 如果文章无id,则直接新建
            if(("https://"+domain_name+"/p/"+link+"/" in link_id_dic.keys()) == False):
                new_post(title, content, link, post_status, terms_names_post_tag, terms_names_category)
                print("new_post==>>", {
                    "title": title, 
                    "content": content, 
                    "link": link, 
                    "post_status": post_status,
                    "terms_names_post_tag": terms_names_post_tag,
                    "terms_names_category": terms_names_category
                });
            # 如果文章有id, 则更新文章
            else:
                # 获取id
                id = link_id_dic["https://"+domain_name+"/p/"+link+"/"]
                edit_post(id, title, content, link, post_status, terms_names_post_tag, terms_names_category)

                print("edit_post==>>", {
                    "id": id, 
                    "title": title, 
                    "content": content,
                    "link": link,
                    "post_status": post_status, 
                    "terms_names_post_tag": terms_names_post_tag,
                    "terms_names_category": terms_names_category
                });
            time.sleep(SLEEP_TIME_BETWEEN_POSTS) # 避免请求过快被服务器拒绝
            # 同步完成后，更新.md_sha1文件
            rebuild_md_sha1_dic_for_md_file(os.path.join(os.getcwd(), ".md_sha1"), md)

    # 4. 重建md_sha1_dic
    rebuild_md_sha1_dic(os.path.join(os.getcwd(), ".md_sha1"), os.path.join(os.getcwd(), "_posts"))
    # 5. 将链接信息写入insert_index_info_in_readme
    insert_index_info_in_readme()

main()
