#!/bin/bash
if [ ! -d _posts  ];then
  mkdir _posts
else
  echo dir exist
fi
echo "请输入文件名 ->"
read -e filename
echo -e "\n"
full_name=$(date "+%Y-%m-%d-%H-%M-%S-$filename.md")
touch  ./_posts/$full_name
file_content="---\ntitle: $filename\ntags:\n- 个人成长\ncategories:\n- 杂谈\n---\n"
echo $full_name
echo -e "\n"
echo -e $file_content > ./_posts/$(date "+%Y-%m-%d-%H-%M-%S-$filename.md")
echo -e $file_content