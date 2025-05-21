---
title: 《树莓派不吃灰》033：为ubuntu server 24.04添加xfce4轻量化桌面配合xrdp实现图形化控制
tags:
- 个人成长
categories:
- 杂谈
---

最近想在树莓派挂机一些网页，比如上一期提到的[《树莓派不吃灰》032：基于Deepseek每天自动算八字，自动生成最合适的摆件显示在办公桌 https://github.com/zhaoolee/pi/blob/main/_posts/2025-05-10-11-29-25-fortune.md](https://github.com/zhaoolee/pi/blob/main/_posts/2025-05-10-11-29-25-fortune.md)

但我的树莓派是安装的ubuntu server 24.04，没有桌面环境，于是本期为ubuntu server24.04添加一个桌面环境。


## 为什么选择xrdp而不是vnc

xrdp对比vnc的优势是在弱网条件下依然有更流畅的表现，rdp传输的是“绘图指令”（逻辑信息），在客户端重建图像，数据量小, 而VNC传输的是“整幅像素图”（图像帧），尤其屏幕变化时数据量巨大。

Windows系统自带rdp的客户端，免费，成本更低。

macOS客户端也有微软提供的rdp的官方客户端，依然免费。



## 同步时间

```
sudo apt install ntpdate -y
sudo ntpdate time.windows.com
```

## 切换到非root用户

```
su - zhaoolee
```


## 安装xfce4 

```
sudo apt install xfce4 xfce4-goodies -y
```

## 配置xrdp


### 什么是RDP（Remote Desktop Protocol）？

RDP是微软（Microsoft）开发的远程桌面协议，用于远程连接 Windows 系统的桌面环境。默认端口是 `3389`，使用的是 Windows 原生的远程桌面服务（Remote Desktop Services / Terminal Services），支持图形加速、剪贴板共享、打印重定向、音频传输等功能客户端：Windows 内置的远程桌面（mstsc.exe），macOS、Linux 也有对应客户端（如 Remmina、Microsoft Remote Desktop）

你在办公室用 Windows 电脑，回家后用笔记本通过远程桌面连接，看到的就是办公室电脑的界面，这背后用的就是 **RDP 协议**。

### 什么是XRDP?



XRDP来自开源社区，用于在 Linux 系统中实现 RDP 协议的服务端功能，让你可以用 Windows 的远程桌面客户端访问 Linux 桌面。支持 RDP 协议，能让 Windows 用户远程访问 Linux 图形桌面，支持多种桌面环境：Xfce、GNOME、KDE、LXDE 等，XRDP本质上是一个“桥梁”，连接 RDP 协议和 Linux 图形环境（如 X11）


在树莓派上装了 Ubuntu Server（无图形界面），装上 `xfce4` 和 `xrdp` 后，就可以用 Windows 的远程桌面工具远程访问这个树莓派的图形界面。

| 项目   | RDP (Microsoft)    | xRDP (Linux)              |
| ---- | ------------------ | ------------------------- |
| 用途   | 远程访问 Windows       | 让 Linux 支持被 RDP 客户端远程访问   |
| 是否开源 | 否                  | 是                         |
| 常用场景 | 远程控制 Windows 电脑    | 控制 Linux 电脑（图形界面） |
| 客户端  | Windows 原生、第三方支持广泛 | 使用 微软开发的RDP远程桌面客户端连接即可  |



### 安装xrdp

```
sudo apt install xrdp -y
```



### 备份配置文件

```
sudo cp /etc/xrdp/xrdp.ini /etc/xrdp/xrdp.ini.bak
```


### 使用3390端口替换默认的的3389 rdp端口


```
sudo sed -i 's/3389/3390/g' /etc/xrdp/xrdp.ini


sudo sed -i 's/max_bpp=32/#max_bpp=32\nmax_bpp=128/g' /etc/xrdp/xrdp.ini


sudo sed -i 's/xserverbpp=24/#xserverbpp=24\nxserverbpp=128/g' /etc/xrdp/xrdp.ini
```

3389是rdp的默认端口，为了防止被扫到，可以自行替换自己喜欢的服务端口

### 查看xrdp状态


```
sudo systemctl status xrdp
```


### 编辑 /etc/xrdp/startwm.sh 默认开机启动xfce4


```
sudo vim /etc/xrdp/startwm.sh
```




注释最后两行，改为使用startxfce4启动


```
#test -x /etc/X11/Xsession && exec /etc/X11/Xsession

#exec /bin/sh /etc/X11/Xsession

startxfce4
```




### 查看xrdp状态


```
sudo systemctl status xrdp
```


### 重启xrdp服务


```
sudo systemctl restart xrdp
```


### 查看3390运行的服务

```
sudo lsof -iTCP:3390 -sTCP:LISTEN
```


## 通过微软的rdp进行连接

![image-20250521095119538](https://cdn.fangyuanxiaozhan.com/assets/1747792279736Y7KMiMzw.png)

![image-20250521095139634](https://cdn.fangyuanxiaozhan.com/assets/1747792299902cKKb2Ae1.png)


ubuntu官方在推广snap安装包，但是snap的沙盒模式，在xfce4配合xrdp的模式下会打不开界面，安装浏览器我们选择非snap版本。


## 安装自由的火狐浏览器

```
# 添加 Mozilla 官方的 PPA 源来安装非 Snap 版本：
sudo add-apt-repository ppa:mozillateam/ppa
sudo apt update
```

编辑 apt 优先级配置：

```
sudo vim /etc/apt/preferences.d/mozilla-firefox
```
填入以下内容
```
Package: firefox*
Pin: release o=LP-PPA-mozillateam
Pin-Priority: 1001
```
安装非snap版本的firefox
```
sudo apt install firefox
```

![image-20250521084600309](https://cdn.fangyuanxiaozhan.com/assets/1747788360795xSwDXBFH.png)

## 安装Chromium浏览器

参考 https://askubuntu.com/questions/1204571/how-to-install-chromium-without-snap/1511695#1511695


```
sudo add-apt-repository ppa:xtradeb/apps -y
sudo apt update
sudo apt install chromium -y
```

![image-20250521093613676](https://cdn.fangyuanxiaozhan.com/assets/174779137445950PJkkD0.png)

## 可以通过右键快速打开安装的浏览器

![image-20250521100651339](https://cdn.fangyuanxiaozhan.com/assets/1747793211688NAfFGkWp.png)

## 小结：

为树莓派添加xfce桌面和浏览器，可以更加充分的压榨树莓派性能，配合frp或zerotier内网穿透，我们可以拥有一款可以随时使用浏览器，画面流畅，私有化的Linux云端电脑。
