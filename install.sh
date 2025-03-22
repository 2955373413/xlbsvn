#!/bin/bash

# SVN安装目录
# svn_dir=/usr/local/svn
svn_plugin_dir=/www/server/panel/plugin/btsvn
svn_repositories=/usr/local/svn/repositories
# 安装SVN
InstallSVN(){
  if command -v yum > /dev/null 2>&1; then
    echo "正在使用yum安装SVN..."
    sudo yum install -y subversion
    # if [ "$?" -ne "0" ]; then
    #   echo "安装SVN失败"
    #   return 1
    # fi
  elif command -v apt > /dev/null 2>&1; then
    echo "正在使用apt安装SVN..."
    sudo apt-get update
    sudo apt-get install -y subversion
    # if [ "$?" -ne "0" ]; then
    #   echo "安装SVN失败"
    #   return 1
    # fi
  else
    echo "Neither yum nor apt found!"
    return 1
  fi

  # 检查并创建目录
  SVN_DIR="/usr/local/svn/repositories"
  if [ ! -d "$SVN_DIR" ]; then
    echo "创建SVN目录..."
    sudo mkdir -p "$SVN_DIR"
    if [ "$?" -ne "0" ]; then
      echo "创建SVN目录失败"
      return 1
    fi
  else
    echo "SVN目录已经存在"
  fi
  
  # 安装Python依赖
  echo "安装Python依赖..."
  pip install requests
  
  # 设置SVN服务自启动
  if [ -f /etc/systemd/system/svnserve.service ]; then
    echo "SVN服务已配置"
  else
    # 创建systemd服务配置
    cat > /tmp/svnserve.service << EOF
[Unit]
Description=Subversion Server
After=network.target

[Service]
Type=forking
ExecStart=/usr/bin/svnserve -d -r $SVN_DIR
Restart=on-abort

[Install]
WantedBy=multi-user.target
EOF
    
    # 复制服务配置文件
    sudo mv /tmp/svnserve.service /etc/systemd/system/
    sudo chmod 644 /etc/systemd/system/svnserve.service
    
    # 重新加载systemd配置
    sudo systemctl daemon-reload
    
    # 设置开机启动
    sudo systemctl enable svnserve
  fi
  
  # 开放SVN端口
  SVN_PORT="3690"
  if command -v firewall-cmd > /dev/null 2>&1 && systemctl is-active firewalld > /dev/null 2>&1; then
    # 使用firewalld
    sudo firewall-cmd --permanent --add-port=$SVN_PORT/tcp
    sudo firewall-cmd --reload
    echo "防火墙已开放端口 $SVN_PORT"
  elif command -v ufw > /dev/null 2>&1 && systemctl is-active ufw > /dev/null 2>&1; then
    # 使用ufw
    sudo ufw allow $SVN_PORT/tcp
    echo "防火墙已开放端口 $SVN_PORT"
  else
    echo "未发现活动的防火墙服务，跳过端口开放"
  fi
    
  # 启动SVN服务
  sudo systemctl start svnserve
  if [ "$?" -ne "0" ]; then
    echo "启动SVN服务失败"
    return 1
  fi

  echo "SVN安装成功"
}
# 卸载SVN
UninstallSVN(){
   # 停止SVN服务
  pkill svnserve
  if [ "$?" -ne "0" ]; then
    echo "停止SVN服务失败"
    # 如果服务没有运行，则不需要退出脚本
  fi
  
  # 删除systemd服务
  if [ -f /etc/systemd/system/svnserve.service ]; then
    sudo systemctl stop svnserve
    sudo systemctl disable svnserve
    sudo rm -f /etc/systemd/system/svnserve.service
    sudo systemctl daemon-reload
  fi

  if command -v yum > /dev/null 2>&1; then
    echo "正在使用yum卸载SVN..."
    svn_package=$(yum list installed | grep subversion | awk '{print $1}')
    sudo yum remove -y ${svn_package}
  elif command -v apt > /dev/null 2>&1; then
    echo "正在使用apt卸载SVN..."
    sudo apt-get remove -y subversion
  else
    echo "Neither yum nor apt found!"
    return 1
  fi
  #删除 svn 插件目录
  if [ -d ${svn_plugin_dir} ]; then
    rm -rf ${svn_plugin_dir}
  fi
  #删除 svn 版本库目录
  if [ -d ${svn_repositories} ]; then
    rm -rf ${svn_repositories}
  fi
  echo "SVN卸载成功"
}

# 根据传入的参数执行相应的函数

action=${1}
if [ "${1}" == 'install' ];then
	InstallSVN
else
    UninstallSVN
fi

