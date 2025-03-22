import os
import subprocess
import public
import shutil
import json
import re
import socket
import time
import requests

class btsvn_main:

    def __init__(self):
        self.svn_dir = "/usr/local/svn/repositories"  # 设置默认的版本库目录
        self.svn_port = "3690"  # 设置默认SVN端口

    def create_repository(self, get):
        """在默认位置创建SVN版本库"""
        if not os.path.exists(self.svn_dir):
            os.makedirs(self.svn_dir)
            print("版本库目录 {} 创建成功".format(self.svn_dir))

        repo_name=get.repo_name
        repo_path = os.path.join(self.svn_dir, repo_name)
        if not os.path.exists(repo_path):
            subprocess.run(['svnadmin', 'create', repo_path], check=True)
            # print(f"版本库 {repo_name} 创建成功。")
            return public.returnMsg(True, '版本库{}创建成功'.format(repo_name))
        else:
            # print(f"版本库 {repo_name} 已存在。")
            return public.returnMsg(True, '该版本库{}已存在'.format(repo_name))

    def configure_repository(self, get):
        """配置指定的版本库"""
        repo_name = get.repo_name
        anon_access = get.anon_access  # 例如："read"
        auth_access = get.auth_access  # 例如："write"
        users = json.loads(get.users)  # 例如：{"username": "password", "anotheruser": "anotherpassword"}
        permissions = json.loads(get.permissions)  # 例如：{"username": "rw", "anotheruser": "r"}
        
        # 自动部署相关参数
        deploy_path = get.deploy_path if hasattr(get, 'deploy_path') else ""
        deploy_script = get.deploy_script if hasattr(get, 'deploy_script') else ""

        repo_path = os.path.join(self.svn_dir, repo_name)
        if not os.path.exists(repo_path):
            return public.returnMsg(False, f'版本库 {repo_name} 不存在')

        # 设置svnserve.conf文件，passwd文件和authz文件
        svnserve_conf_path = os.path.join(repo_path, 'conf', 'svnserve.conf')
        passwd_path = os.path.join(repo_path, 'conf', 'passwd')
        authz_path = os.path.join(repo_path, 'conf', 'authz')

        # 配置svnserve.conf文件
        with open(svnserve_conf_path, 'w') as conf_file:
            conf_file.write("[general]\n")
            conf_file.write(f"anon-access = {anon_access}\n")
            conf_file.write(f"auth-access = {auth_access}\n")
            conf_file.write("password-db = passwd\n")
            conf_file.write("authz-db = authz\n")
            conf_file.write("realm = My SVN Repository\n")

        # 添加用户到passwd文件
        with open(passwd_path, 'w') as passwd_file:
            passwd_file.write("[users]\n")
            for username, password in users.items():
                passwd_file.write(f"{username} = {password}\n")

        # 设置权限到authz文件
        with open(authz_path, 'w') as authz_file:
            authz_file.write("[/]\n")
            for username, permission in permissions.items():
                authz_file.write(f"{username} = {permission}\n")
        
        # 如果有部署路径，配置自动部署
        if deploy_path:
            # 创建部署路径和日志目录
            deploy_log_dir = os.path.join(deploy_path, 'log')
            if not os.path.exists(deploy_path):
                os.makedirs(deploy_path)
            if not os.path.exists(deploy_log_dir):
                os.makedirs(deploy_log_dir)
            
            # 创建用户自定义部署脚本
            deploy_shell_init = f"""#!/bin/bash
cd {deploy_path}
{deploy_script}
"""
            # 用户自定义部署脚本
            hooks_path = os.path.join(repo_path, 'hooks')
            customer_script_path = os.path.join(hooks_path, 'customer_shell.sh')
            with open(customer_script_path, 'w') as f:
                f.write(deploy_shell_init)
            subprocess.run(['chmod', '755', customer_script_path], check=True)
            
            # 创建部署脚本
            # 获取用户名和密码
            username = list(users.keys())[0]
            password = users[username]
            
            # 部署脚本
            post_commit_script = f"""#!/bin/bash
DeployPath='{deploy_path}'
SVNRepository='{repo_path}'
LogPath='{deploy_log_dir}'
User='{username}'
Password='{password}'

# 设置正确的语言环境
export LANG='en_US.UTF-8'
export LC_ALL='en_US.UTF-8'

# 记录日志的函数
log() {{
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1" >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log"
}}

log "开始部署 {repo_name}"
log "进入部署目录: $DeployPath"
cd $DeployPath || {{
    log "切换到部署目录失败"
    exit 1
}}

log "清理可能存在的冲突"
svn cleanup

log "检出最新代码"
svn checkout --non-interactive --trust-server-cert svn://127.0.0.1:{self.svn_port}/{repo_name} . --username "$User" --password "$Password" >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log" 2>&1
if [ $? -ne 0 ]; then
    log "检出代码失败"
    exit 1
fi

log "恢复所有修改"
svn revert --recursive .

log "更新代码"
svn update --non-interactive --trust-server-cert --username "$User" --password "$Password" . >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log" 2>&1
if [ $? -ne 0 ]; then
    log "更新代码失败"
    exit 1
fi

log "设置文件权限"
chown -R www:www $DeployPath

log "运行自定义部署脚本"
. $SVNRepository/hooks/customer_shell.sh >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log" 2>&1
if [ $? -ne 0 ]; then
    log "自定义脚本执行失败"
else
    log "自定义脚本执行成功"
fi

log "部署完成"
"""
            # 写入部署脚本
            post_commit_path = os.path.join(hooks_path, 'post-commit')
            with open(post_commit_path, 'w') as f:
                f.write(post_commit_script)
            subprocess.run(['chmod', '755', post_commit_path], check=True)
        
        # 保存部署配置到配置文件
        config_file = os.path.join(repo_path, 'conf', 'config.json')
        config = {
            'deploy_path': deploy_path,
            'deploy_script': deploy_script
        }
        with open(config_file, 'w') as f:
            json.dump(config, f)

        return public.returnMsg(True, f'版本库 {repo_name} 配置成功。')


    def create_and_configure_repository(self, get):
        """在默认位置创建并配置SVN版本库"""
        repo_name = get.repo_name

        # 创建版本库
        create_result = self.create_repository(get)
        if not create_result['status']:
            return create_result

        # 配置版本库
        configure_result = self.configure_repository(get)
        return configure_result


    def get_svn_status(self,get):
        """获取SVN服务状态"""
        try:
            status_output = subprocess.check_output(['ps', '-ef'], text=True)
            if "svnserve" in status_output:
                return public.returnMsg(True, 'SVN服务正在运行')
            else:
                return public.returnMsg(False, 'SVN服务未运行')
        except subprocess.CalledProcessError as e:
            return public.returnMsg(False, '获取SVN服务状态失败')

    def stop_svn_service(self,get):
        """停止SVN服务"""
        try:
            subprocess.run(['pkill', 'svnserve'], check=True)
            return public.returnMsg(True, 'SVN服务已停止')
        except subprocess.CalledProcessError as e:
            return public.returnMsg(False, '停止SVN服务失败')

    def start_svn_service(self,get):
        """启动SVN服务"""
        try:
            subprocess.run(['svnserve', '-d', '-r', self.svn_dir], check=True)
            return public.returnMsg(True, 'SVN服务已启动')
        except subprocess.CalledProcessError as e:
            return public.returnMsg(False, '启动SVN服务失败')

    def restart_svn_service(self,get):
        """重启SVN服务"""
        stop_result = self.stop_svn_service(get)
        if not stop_result['status']:
            return stop_result

        start_result = self.start_svn_service(get)
        return start_result

    def list_repositories(self,get):
        """列出所有版本库"""
        if os.path.exists(self.svn_dir):
            return public.returnMsg(True, os.listdir(self.svn_dir))
        else:
            return public.returnMsg(False, '版本库目录不存在')

    def delete_repository(self, get):
        """删除指定的版本库"""
        repo_name = get.repo_name
        repo_path = os.path.join(self.svn_dir, repo_name)
        if os.path.exists(repo_path):
            # 检查是否有部署路径，如果有，清理.svn目录
            config_file = os.path.join(repo_path, 'conf', 'config.json')
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    if config.get('deploy_path'):
                        svn_dir = os.path.join(config['deploy_path'], '.svn')
                        if os.path.exists(svn_dir):
                            shutil.rmtree(svn_dir)
                except Exception as e:
                    pass  # 忽略配置文件读取错误
            
            shutil.rmtree(repo_path)
            return public.returnMsg(True, '版本库 {} 删除成功'.format(repo_name))
        else:
            return public.returnMsg(False, '版本库 {} 不存在'.format(repo_name))
    
    def parse_config(self, config):
        """解析配置文件，提取参数值"""
        params = {}
        lines = config.split('\n')
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                # 将短横线替换为下划线
                key = key.replace('-', '_')
                params[key.strip()] = value.strip()
        return params

    def parse_users(self, users):
        """解析用户信息，提取用户名和密码"""
        user_dict = {}
        lines = users.split('\n')
        for line in lines:
            if '=' in line:
                username, password = line.split('=', 1)
                user_dict[username.strip()] = password.strip()
        return user_dict

    def parse_authz(self, authz):
        """解析权限信息，提取用户名和权限"""
        authz_dict = {}
        lines = authz.split('\n')
        for line in lines:
            if '=' in line:
                username, permission = line.split('=', 1)
                authz_dict[username.strip()] = permission.strip()
        return authz_dict

    def format_config(self, config, file_type):
        """将参数转换为配置文件的格式，根据不同文件类型进行特定处理。"""
        lines = []
        if file_type == "authz":
            lines.append("[/]")
            for key, value in config.items():
                lines.append(f'{key} = {value}')
        elif file_type == "passwd":
            lines.append("[users]")
            for key, value in config['users'].items():
                lines.append(f'{key} = {value}')
        elif file_type == "svnserve":
            lines.append("[general]")
            for key, value in config.items():
                lines.append(f'{key} = {value}')
        return '\n'.join(lines)

    def modify_repository_config(self, get):
        """修改指定版本库的配置信息"""
        repo_name = get.repo_name
        svnserve_conf = {
            "anon-access": get.anon_access,
            "auth-access": get.auth_access,
            "password-db": "passwd",
            "authz-db": "authz",
            "realm": "My SVN Repository"
        }
        users = json.loads(get.users)
        passwd = {"users": users}
        authz = json.loads(get.permissions)  # 例如：{"username": "rw", "anotheruser": "r"}
        
        # 获取部署路径和部署脚本
        deploy_path = get.deploy_path if hasattr(get, 'deploy_path') else ""
        deploy_script = get.deploy_script if hasattr(get, 'deploy_script') else ""

        svnserve_conf = self.format_config(svnserve_conf, "svnserve")
        passwd = self.format_config(passwd, "passwd")
        authz = self.format_config(authz, "authz")

        repo_path = os.path.join(self.svn_dir, repo_name)
        if not os.path.exists(repo_path):
            return public.returnMsg(False, f'版本库 {repo_name} 不存在')

        # 获取svnserve.conf文件，passwd文件和authz文件的路径
        svnserve_conf_path = os.path.join(repo_path, 'conf', 'svnserve.conf')
        passwd_path = os.path.join(repo_path, 'conf', 'passwd')
        authz_path = os.path.join(repo_path, 'conf', 'authz')

        # 写入新的配置信息
        with open(svnserve_conf_path, 'w') as conf_file:
            conf_file.write(svnserve_conf)
        with open(passwd_path, 'w') as passwd_file:
            passwd_file.write(passwd)
        with open(authz_path, 'w') as authz_file:
            authz_file.write(authz)
            
        # 读取原配置
        config_file = os.path.join(repo_path, 'conf', 'config.json')
        old_config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    old_config = json.load(f)
            except:
                old_config = {}
        
        # 如果部署路径发生变化，清理旧部署路径的.svn目录
        old_deploy_path = old_config.get('deploy_path', '')
        if old_deploy_path and old_deploy_path != deploy_path and os.path.exists(old_deploy_path):
            old_svn_dir = os.path.join(old_deploy_path, '.svn')
            if os.path.exists(old_svn_dir):
                shutil.rmtree(old_svn_dir)
        
        # 更新配置
        new_config = {
            'deploy_path': deploy_path,
            'deploy_script': deploy_script
        }
        with open(config_file, 'w') as f:
            json.dump(new_config, f)
        
        # 如果有部署路径，更新自动部署
        if deploy_path:
            # 创建部署路径和日志目录
            deploy_log_dir = os.path.join(deploy_path, 'log')
            if not os.path.exists(deploy_path):
                os.makedirs(deploy_path)
            if not os.path.exists(deploy_log_dir):
                os.makedirs(deploy_log_dir)
            
            # 创建用户自定义部署脚本
            deploy_shell_init = f"""#!/bin/bash
cd {deploy_path}
{deploy_script}
"""
            # 用户自定义部署脚本
            hooks_path = os.path.join(repo_path, 'hooks')
            customer_script_path = os.path.join(hooks_path, 'customer_shell.sh')
            with open(customer_script_path, 'w') as f:
                f.write(deploy_shell_init)
            subprocess.run(['chmod', '755', customer_script_path], check=True)
            
            # 获取用户名和密码
            username = list(users.keys())[0]
            password = users[username]
            
            # 部署脚本
            post_commit_script = f"""#!/bin/bash
DeployPath='{deploy_path}'
SVNRepository='{repo_path}'
LogPath='{deploy_log_dir}'
User='{username}'
Password='{password}'

# 设置正确的语言环境
export LANG='en_US.UTF-8'
export LC_ALL='en_US.UTF-8'

# 记录日志的函数
log() {{
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1" >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log"
}}

log "开始部署 {repo_name}"
log "进入部署目录: $DeployPath"
cd $DeployPath || {{
    log "切换到部署目录失败"
    exit 1
}}

log "清理可能存在的冲突"
svn cleanup

log "检出最新代码"
svn checkout --non-interactive --trust-server-cert svn://127.0.0.1:{self.svn_port}/{repo_name} . --username "$User" --password "$Password" >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log" 2>&1
if [ $? -ne 0 ]; then
    log "检出代码失败"
    exit 1
fi

log "恢复所有修改"
svn revert --recursive .

log "更新代码"
svn update --non-interactive --trust-server-cert --username "$User" --password "$Password" . >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log" 2>&1
if [ $? -ne 0 ]; then
    log "更新代码失败"
    exit 1
fi

log "设置文件权限"
chown -R www:www $DeployPath

log "运行自定义部署脚本"
. $SVNRepository/hooks/customer_shell.sh >> "$LogPath/svn_deploy_$(date +"%Y%m%d").log" 2>&1
if [ $? -ne 0 ]; then
    log "自定义脚本执行失败"
else
    log "自定义脚本执行成功"
fi

log "部署完成"
"""
            # 写入部署脚本
            post_commit_path = os.path.join(hooks_path, 'post-commit')
            with open(post_commit_path, 'w') as f:
                f.write(post_commit_script)
            subprocess.run(['chmod', '755', post_commit_path], check=True)

        return public.returnMsg(True, f'版本库 {repo_name} 配置已修改。')

    def view_repository_commits(self, get):
        """查看指定版本库的提交记录"""
        repo_name = get.repo_name
        repo_path = os.path.join(self.svn_dir, repo_name)
        if not os.path.exists(repo_path):
            return public.returnMsg(False, f'版本库 {repo_name} 不存在')

        # 执行svn log命令
        result = subprocess.run(['svn', 'log', repo_path], capture_output=True, text=True)

        # 解析命令的输出
        commits = []
        for entry in result.stdout.split('------------------------------------------------------------------------'):
            lines = entry.strip().split('\n')
            if len(lines) > 1:
                revision, author, date = lines[0].split('|')[:3]
                message = '\n'.join(lines[1:])
                commit = {
                    'revision': revision.strip(),
                    'author': author.strip(),
                    'date': date.strip(),
                    'message': message.strip()
                }
                commits.append(commit)

        return public.returnMsg(True, commits)

    def view_all_repository_configs(self, get):
        """查看所有版本库的配置信息"""
        repos = self.list_repositories(get)
        if not repos['status']:
            return repos

        configs = []
        for repo_name in repos['msg']:
            get.repo_name = repo_name
            config = self.view_repository_config(get)
            if config['status']:
                config['msg']['repo_name'] = repo_name
                configs.append(config['msg'])

        return public.returnMsg(True, configs)

    def view_repository_config(self, get):
        """查看指定版本库的配置信息"""
        repo_name = get.repo_name
        repo_path = os.path.join(self.svn_dir, repo_name)
        if not os.path.exists(repo_path):
            return public.returnMsg(False, f'版本库 {repo_name} 不存在')

        # 获取svnserve.conf文件，passwd文件和authz文件的路径
        svnserve_conf_path = os.path.join(repo_path, 'conf', 'svnserve.conf')
        passwd_path = os.path.join(repo_path, 'conf', 'passwd')
        authz_path = os.path.join(repo_path, 'conf', 'authz')
        config_path = os.path.join(repo_path, 'conf', 'config.json')

        # 读取并解析配置文件的内容
        with open(svnserve_conf_path, 'r') as conf_file:
            svnserve_conf = self.parse_config(conf_file.read())
        with open(passwd_path, 'r') as passwd_file:
            passwd = self.parse_users(passwd_file.read())
        with open(authz_path, 'r') as authz_file:
            authz = self.parse_authz(authz_file.read())

        # 读取部署配置
        deploy_path = ""
        deploy_script = ""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                deploy_path = config_data.get('deploy_path', '')
                deploy_script = config_data.get('deploy_script', '')
            except:
                pass
                
        # 获取服务器IP和端口
        ip = self.get_server_ip()
        svn_url = f"svn://{ip}:{self.svn_port}/{repo_name}"

        return public.returnMsg(True, {
            'anon_access': svnserve_conf.get('anon_access'),
            'auth_access': svnserve_conf.get('auth_access'),
            'users': passwd,
            'permissions': authz,
            'deploy_path': deploy_path,
            'deploy_script': deploy_script,
            'svn_url': svn_url
        })
        
    def get_server_ip(self):
        """获取服务器IP地址"""
        try:
            # 首先尝试获取公网IP
            response = requests.get('https://api.ipify.org', timeout=5)
            if response.status_code == 200:
                return response.text.strip()
            
            # 如果获取公网IP失败，尝试获取本地IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            # 所有方法失败，返回本地IP
            return '127.0.0.1'
            
    def get_deploy_logs(self, get):
        """获取部署日志"""
        repo_name = get.repo_name
        repo_path = os.path.join(self.svn_dir, repo_name)
        if not os.path.exists(repo_path):
            return public.returnMsg(False, f'版本库 {repo_name} 不存在')
        
        config_path = os.path.join(repo_path, 'conf', 'config.json')
        deploy_path = ""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                deploy_path = config_data.get('deploy_path', '')
            except:
                pass
        
        if not deploy_path:
            return public.returnMsg(False, '该版本库未配置自动部署')
        
        log_dir = os.path.join(deploy_path, 'log')
        if not os.path.exists(log_dir):
            return public.returnMsg(False, '部署日志目录不存在')
        
        # 获取最新的日志文件
        today = time.strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f'svn_deploy_{today}.log')
        if not os.path.exists(log_file):
            # 查找最近的日志文件
            log_files = os.listdir(log_dir)
            if not log_files:
                return public.returnMsg(False, '暂无部署日志')
            log_files.sort(reverse=True)
            log_file = os.path.join(log_dir, log_files[0])
        
        # 读取日志内容
        with open(log_file, 'r') as f:
            log_content = f.read()
        
        return public.returnMsg(True, log_content)