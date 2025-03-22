#!/usr/bin/python
# coding: utf-8

# +--------------------------------------------------------------------
# |   SVN项目部署工具
# +-------------------------------------------------------------------
# |   Author: 技术雨 <forxiaoyu@qq.com>
# +--------------------------------------------------------------------

import sys,os,json
if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
elif sys.version_info[0] == 3:
    from importlib import reload
    reload(sys)

#设置运行目录
plugin_path = os.path.dirname(os.path.abspath(__file__))
panel_path = os.path.dirname(os.path.dirname(plugin_path))
os.chdir(panel_path);

#添加包引用位置并引用公共包
sys.path.append("class/")
import public,db,time

#在非命令行模式下引用面板缓存和session对象
if __name__ != '__main__':
    from BTPanel import cache,session,redirect

class svn_deploy_main:
    __plugin_path = "%s/" % (plugin_path)
    __config = None
    __db_path = "%s/data/svn_deploy.db" % (panel_path)
    __svn_home = '/www/svn'
    __svn_conf_path = '/www/svn/conf'
    __svn_repository_path = '/www/svn/repository'
    __svn_port = '3690'
    __svn_port_info = 'SVN项目部署工具端口'

    #构造方法
    def  __init__(self):
        self.__init_config()

    # 初始化配置
    def __init_config(self):
        if self.__config: return;
        self.__config = self.__get_config(None,True);
        return self.__config

    # 获取首页
    def get_index(self,args):
        if not 'p' in args: args.p = 1
        if not 'rows' in args: args.rows = 10
        if not 'title' in args: args.title = ''
        args.p = int(args.p)
        args.rows = int(args.rows)
        args.title = public.checkInput(args.title)

        if not os.path.exists(self.__svn_repository_path):
            return {
                "code":0,
                "msg":"仓库目录不存在",
            }

        repo_list_src = os.listdir(self.__svn_repository_path)

        repo_list = []
        for repo in repo_list_src:
            if args.title in repo:
                repo_list.append(repo)

        count = len(repo_list)

        page_data = public.get_page(count,p=args.p,rows=args.rows,callback='svn_deploy.get_index',result='1,2,3,4,5,8')

        index = (args.p - 1)*args.rows
        repo_list = repo_list[index:index+args.rows]

        base_url = 'svn://%s/' % (public.GetLocalIp())

        repo_data = []
        for repo in repo_list:

            path = self.__svn_repository_path+'/'+repo
            project_data_file = path+'/conf/config.json'
            if not os.path.exists(project_data_file):
                project_config = {
                    'project_path': '',
                    'deploy_shell' : '',
                }
            project_config = public.ReadFile(project_data_file)
            if not project_config:
                project_config = {
                    'project_path': '',
                    'deploy_shell' : '',
                }
            project_config = json.loads(project_config)
            # project_config = {
            #     'project_path': '',
            #     'deploy_shell' : '',
            # }
            repo_data.append({'title':repo,'repo_path':base_url+repo,'path':path,'project_path':project_config['project_path'],'deploy_shell':project_config['deploy_shell']})

        data = {'list':repo_data,'page':page_data['page'],'title':args.title}
        return {
            "code":1,
            "msg":"操作成功",
            "total":len(repo_data),
            "data":data,
        }

    # 添加项目
    def add_project(self,args):
        if not 'title' in args: args.title = ''
        if not 'project_path' in args: args.project_path = ''
        if not 'deploy_shell' in args: args.deploy_shell = ''
        args.deploy_shell = args.deploy_shell.replace('\r','')

        if not all([args.title,args.project_path]):
            return {'code':0,'msg':'参数错误'}

        repo_path = self.__svn_repository_path+'/'+args.title

        if os.path.exists(repo_path):
            return {'code':0,'msg':'项目目录已存在'}

        public.ExecShell('svnadmin create %s' % (repo_path))

        public.ExecShell('sed -i "s/# anon-access = read/anon-access = none/g;s/# password-db = passwd/password-db = %s/g;s/# authz-db = authz/authz-db = %s/g" %s' % (
            (self.__svn_conf_path+'/passwd').replace('/','\/')
            ,(self.__svn_conf_path+'/authz').replace('/','\/')
            ,repo_path+'/conf/svnserve.conf'
            ))

        deploy_shell_init = '''#!/bin/bash
cd %s
%s
''' % (args.project_path,args.deploy_shell.replace('$','\$'))
        # 用户自定义部署脚本
        public.ExecShell('echo "%s" > %s/hooks/customer_shell.sh && chmod 777 %s/hooks/customer_shell.sh' % (deploy_shell_init,repo_path,repo_path))


        deploy_shell_default = '''#!/bin/bash
DeployPath='%s'
SVNRepository='%s'
User='%s'
Password='%s'
export LANG='zh_CN.UTF-8'
cd \$DeployPath
svn cleanup
svn checkout svn://127.0.0.1/%s . --username \$User --password \$Password
svn revert --recursive .
svn update .
chown -R www:www \$DeployPath

. \$SVNRepository/hooks/customer_shell.sh

''' % (args.project_path,repo_path,"root",self.__get_ini('passwd','users','root'),args.title)
        # return deploy_shell_default
        # 部署脚本
        public.ExecShell('echo "%s" > %s/hooks/post-commit && chmod 777 %s/hooks/post-commit' % (deploy_shell_default,repo_path,repo_path))

        # 记录项目配置
        project_config = {
            'project_path': args.project_path,
            'deploy_shell' : args.deploy_shell,
        }
        project_data_file = repo_path+'/conf/config.json'
        public.WriteFile(project_data_file,json.dumps(project_config))

        # 设置root访问权限
        project_auth_title = args.title+':/'
        self.__del_ini('authz',project_auth_title,'')
        self.__set_ini('authz',project_auth_title,'','')
        self.__set_ini('authz',project_auth_title,'root','rw')

        return {'code':1,'msg':'操作成功'}

    # 编辑项目
    def edit_project(self,args):
        if not 'title' in args: args.title = ''
        if not 'old_title' in args: args.old_title = ''
        if not 'project_path' in args: args.project_path = ''
        if not 'old_project_path' in args: args.old_project_path = ''
        if not 'deploy_shell' in args: args.deploy_shell = ''
        if not 'old_deploy_shell' in args: args.old_deploy_shell = ''
        args.deploy_shell = args.deploy_shell.replace('\r','')
        args.old_deploy_shell = args.old_deploy_shell.replace('\r','')

        if not all([args.title,args.project_path,args.old_project_path]):
            return {'code':0,'msg':'参数错误'}

        if args.title != args.old_title:

            if os.path.exists(self.__svn_repository_path+'/'+args.title):
                return {'code':0,'msg':'项目目录已存在'}

            public.ExecShell('mv %s/%s %s/%s' % (self.__svn_repository_path,args.old_title,self.__svn_repository_path,args.title))

            authz = self.__get_ini('authz','','')
            auth_old_title = args.old_title+':/'
            auth_title = args.title+':/'
            if auth_old_title in authz:
                auth = self.__get_ini('authz',auth_old_title,'')
                self.__del_ini('authz',auth_title,'')
                self.__set_ini('authz',auth_title,'','')
                for key in auth:
                    self.__set_ini('authz',auth_title,key[0],key[1])

                self.__del_ini('authz',auth_old_title,'')

        repo_path = self.__svn_repository_path+'/'+args.title

        deploy_shell_init = '''#!/bin/bash
cd %s
%s
''' % (args.project_path,args.deploy_shell.replace('$','\$'))
        # 用户自定义部署脚本
        public.ExecShell('echo "%s" > %s/hooks/customer_shell.sh && chmod 777 %s/hooks/customer_shell.sh' % (deploy_shell_init,repo_path,repo_path))


        deploy_shell_default = '''#!/bin/bash
DeployPath='%s'
SVNRepository='%s'
User='%s'
Password='%s'
export LANG='zh_CN.UTF-8'
cd \$DeployPath
# svn cleanup
svn checkout svn://127.0.0.1/%s . --username \$User --password \$Password
svn revert --recursive .
svn update .
chown -R www:www \$DeployPath

. \$SVNRepository/hooks/customer_shell.sh

''' % (args.project_path,repo_path,"root",self.__get_ini('passwd','users','root'),args.title)
        # return deploy_shell_default
        # 部署脚本
        public.ExecShell('echo "%s" > %s/hooks/post-commit && chmod 777 %s/hooks/post-commit' % (deploy_shell_default,repo_path,repo_path))

        if args.project_path != args.old_project_path or args.deploy_shell != args.old_deploy_shell:
            # 记录项目配置
            project_config = {
                'project_path': args.project_path,
                'deploy_shell' : args.deploy_shell,
            }
            project_data_file = repo_path+'/conf/config.json'
            public.WriteFile(project_data_file,json.dumps(project_config))

        # 部署目录变更，清楚原目录.svn
        if args.project_path != args.old_project_path:
            public.ExecShell('rm -rf %s/.svn' % (args.old_project_path))

        return {'code':1,'msg':'操作成功'}

    # 删除项目
    def del_project(self,args):
        if not 'title' in args: args.title = ''

        if args.title == '':
            return {'code':0,'msg':'参数错误'}

        repo_path = self.__svn_repository_path+'/'+args.title

        if not os.path.exists(repo_path):
            return {'code':0,'msg':'项目目录不存在'}

        # 清理部署目录
        project_data_file = repo_path+'/conf/config.json'
        project_config = public.ReadFile(project_data_file)
        project_config = json.loads(project_config)
        public.ExecShell('rm -rf %s/.svn' % (project_config['project_path']))

        public.ExecShell('rm -rf %s' % (repo_path))

        self.__del_ini('authz',args.title+':/','')

        return {'code':1,'msg':'操作成功'}

    # 授权管理
    def access_project(self,args):
        if not 'title' in args: args.title = ''

        authz = self.__get_ini('authz','','')

        project_auth_title = args.title+':/'

        if project_auth_title not in authz:
            self.__set_ini('authz',project_auth_title,'','')
            data = {}
        else:
            data = self.__get_ini('authz',project_auth_title,'')

        users = self.__get_ini('passwd','users','')
        for user in users:
            if 'root' == user[0]:
                users.remove(user)
                break

        project_auth = self.__get_ini('authz',project_auth_title,'')

        project_auth_dict = {}
        for auth in project_auth:
            project_auth_dict[auth[0]] = auth[1]

        return {'code':1,'msg':'操作成功','data':data,'users':users,'title':args.title,'project_auth_dict':project_auth_dict}

    # 仓库授权
    def access_project_act(self,args):
        if not 'svn__title' in args: args.svn__title = ''

        if args.svn__title == '':
            return {'code':0,'msg':'项目不存在'}

        project_auth_title = args.svn__title+':/'

        self.__del_ini('authz',project_auth_title,'')
        self.__set_ini('authz',project_auth_title,'','')
        # 设置root访问权限
        self.__set_ini('authz',project_auth_title,'root','rw')

        users = self.__get_ini('passwd','users','')
        for user in users:
            if user[0] in args:
                if int(args[user[0]]) == 1:
                    self.__set_ini('authz',project_auth_title,user[0],'r')
                elif int(args[user[0]]) == 2:
                    self.__set_ini('authz',project_auth_title,user[0],'rw')

        return {
            "code":1,
            "msg":"操作成功",
        }

    # 账号管理
    def get_account(self,args):

        if not 'p' in args: args.p = 1
        if not 'rows' in args: args.rows = 10
        if not 'title' in args: args.title = ''
        args.p = int(args.p)
        args.rows = int(args.rows)
        args.title = public.checkInput(args.title)

        if not os.path.exists(self.__svn_conf_path+'/passwd'):
            return {
                "code":0,
                "msg":"账号信息不存在",
            }

        user_list_src = self.__get_ini('passwd','users','')

        user_list = []
        for user in user_list_src:
            if args.title in user[0]:
                user_list.append(user)

        count = len(user_list)

        page_data = public.get_page(count,p=args.p,rows=args.rows,callback='svn_deploy.get_account',result='1,2,3,4,5,8')

        index = (args.p - 1)*args.rows
        user_list = user_list[index:index+args.rows]

        user_data = []
        for user in user_list:
            user_data.append({'user':user[0],'passwd':user[1]})

        data = {'list':user_data,'page':page_data['page'],'title':args.title}
        return {
            "code":1,
            "msg":"操作成功",
            "total":len(user_data),
            "data":data,
        }

    # 添加账号
    def add_account(self,args):
        if not 'user' in args: args.user = ''
        if not 'passwd' in args: args.passwd = ''

        if not all([args.user,args.passwd]):
            return {'code':0,'msg':'参数错误'}

        users = self.__get_ini('passwd','users','')
        if args.user in users:
            return {'code':0,'msg':'用户已存在'}

        # 限制密码长度
        if len(args.passwd) < 8:
            return {'code':0,'msg':'密码长度需大于等于8位'}

        self.__set_ini('passwd','users',args.user,args.passwd)

        return {
            "code":1,
            "msg":"操作成功",
        }

    # 编辑账号
    def edit_account(self,args):
        if not 'user' in args: args.user = ''
        if not 'old_user' in args: args.old_user = ''
        if not 'passwd' in args: args.passwd = ''
        if not 'old_passwd' in args: args.old_passwd = ''

        if not all([args.user,args.passwd]):
            return {'code':0,'msg':'参数错误'}

        # users = self.__get_ini('passwd','users','')
        # if args.user in users:
        #     return {'code':0,'msg':'用户已存在'}

        # 限制密码长度
        if len(args.passwd) < 8:
            return {'code':0,'msg':'密码长度需大于等于8位'}

        if args.user != args.old_user:
            if args.old_user == 'root':
                return {'code':0,'msg':'root账户名不可修改'}
            else:
                self.__del_ini('passwd','users',args.old_user)

                authz = self.__get_ini('authz','','')
                for auth in authz:
                    if auth == 'aliases' or auth == 'groups':
                        continue
                    user_auth = self.__get_ini('authz',auth,args.old_user)
                    if user_auth != '':
                        self.__del_ini('authz',auth,args.old_user)
                        self.__set_ini('authz',auth,args.user,user_auth)

        self.__set_ini('passwd','users',args.user,args.passwd)

        # 更新脚本
        if args.passwd != args.old_passwd and args.old_user == 'root':
            repo_list = os.listdir(self.__svn_repository_path)
            for repo in repo_list:
                repo_path = self.__svn_repository_path+'/'+repo
                if os.path.exists(repo_path+'/hooks/post-commit'):
                    project_data_file = repo_path+'/conf/config.json'
                    project_config = public.ReadFile(project_data_file)
                    project_config = json.loads(project_config)
                    deploy_shell_default = '''#!/bin/bash
DeployPath='%s'
SVNRepository='%s'
User='%s'
Password='%s'
export LANG='zh_CN.UTF-8'
cd \$DeployPath
# svn cleanup
svn checkout svn://127.0.0.1/%s . --username \$User --password \$Password
svn revert --recursive .
svn update .
chown -R www:www \$DeployPath

. \$SVNRepository/hooks/customer_shell.sh

''' % (project_config['project_path'],repo_path,"root",self.__get_ini('passwd','users','root'),repo)
                    # return deploy_shell_default
                    # 部署脚本
                    public.ExecShell('echo "%s" > %s/hooks/post-commit && chmod 777 %s/hooks/post-commit' % (deploy_shell_default,repo_path,repo_path))

        return {
            "code":1,
            "msg":"操作成功",
        }

    # 删除账号
    def del_account(self,args):
        if not 'user' in args: args.user = ''
        if not all([args.user]):
            return {'code':0,'msg':'参数错误'}

        if args.user == 'root':
            return {'code':0,'msg':'root账户不可删除'}

        self.__del_ini('passwd','users',args.user)

        authz = self.__get_ini('authz','','')
        for auth in authz:
            if auth == 'aliases' or auth == 'groups':
                continue
            user_auth = self.__get_ini('authz',auth,args.user)
            if user_auth != '':
                self.__del_ini('authz',auth,args.user)

        return {
            "code":1,
            "msg":"操作成功",
        }

    # 高级设置
    def get_system(self,args):
        svn_service_status = public.ExecShell("systemctl status svnserve|grep 'Active:'")
        if svn_service_status[1] == '' and 'running' in svn_service_status[0]:
            svn_service_status = 1
        else:
            svn_service_status = 0

        return {
            "code":1,
            "msg":"操作成功",
            "data":{
                "svn_service_status":svn_service_status,
                "svn_service_port":self.__svn_port,
            }
        }

    # 高级设置操作
    def get_system_act(self,args):
        return {
            "code":1,
            "msg":"操作成功",
        }

    # 修改服务状态
    def get_service_act(self,args):
        if not 'status' in args : args.status = 1
        args.status = int(args.status)

        if args.status == 1:
            # 启动服务
            serviceInfo = public.ExecShell('systemctl start svnserve')
        elif args.status == 2:
            # 重启服务
            serviceInfo = public.ExecShell('systemctl restart svnserve')
        elif args.status == 3:
            # 关闭服务
            serviceInfo = public.ExecShell('systemctl stop svnserve')
        else:
            # 启动服务
            serviceInfo = public.ExecShell('systemctl start svnserve')

        if serviceInfo[1] == '':
            return {
                "code":1,
                "msg":"操作成功",
            }
        else:
            return {
                "code":0,
                "msg":"操作失败",
            }

    # 修复插件
    def get_fix(self,args):
        self.install()
        return {"code":1,"msg":"修复完成"}

    # 获取服务器信息
    def __get_serverid(self):
        import panelAuth
        auth = panelAuth.panelAuth()
        return auth.create_serverid({})

    # 获取插件购买状态
    def __get_payinfo(self):
        import panelPlugin
        plugin = panelPlugin.panelPlugin()
        state = plugin.getEndDate('svn_deploy')
        if state in ['未开通','待支付','已到期']:
            return False
        else:
            return True

    #读取配置项(插件自身的配置文件)
    #@param key 取指定配置项，若不传则取所有配置[可选]
    #@param force 强制从文件重新读取配置项[可选]
    def __get_config(self,key=None,force=False):
        #判断是否从文件读取配置
        if not self.__config or force:
            config_file = self.__plugin_path + 'config.json'
            if not os.path.exists(config_file):
                default = {}
                public.writeFile(config_file,json.dumps(default));
            if not os.path.exists(config_file): return None
            f_body = public.ReadFile(config_file)
            if not f_body: return None
            self.__config = json.loads(f_body)

        #取指定配置项
        if key:
            if key in self.__config: return self.__config[key]
            return None
        return self.__config

    #设置配置项(插件自身的配置文件)
    #@param key 要被修改或添加的配置项[可选]
    #@param value 配置值[可选]
    def __set_config(self,key=None,value=None):
        #是否需要初始化配置项
        if not self.__config: self.__config = {}

        #是否需要设置配置值
        if key:
            self.__config[key] = value

        #写入到配置文件
        config_file = self.__plugin_path + 'config.json'
        public.WriteFile(config_file,json.dumps(self.__config))
        return True

    # 获取ini项
    def __get_ini(self,file,section,key):
        import configparser
        config = configparser.ConfigParser()
        config.read(self.__svn_conf_path+'/'+file)

        if section == '':
            return config.sections()

        if section not in config:
            return ''

        if key == '':
            return config.items(section)

        if key not in config[section]:
            return ''

        return config.get(section,key)

    # 设置ini项
    def __set_ini(self,file,section,key,value):
        import configparser
        config = configparser.ConfigParser()
        config.read(self.__svn_conf_path+'/'+file)
        if key == '':
            config.add_section(section)
        else:
            config.set(section,key,value)
        with open(self.__svn_conf_path+'/'+file,'w') as f:
            config.write(f)
        return True

    # 删除ini项
    def __del_ini(self,file,section,key):
        import configparser
        config = configparser.ConfigParser()
        config.read(self.__svn_conf_path+'/'+file)

        if key == '':
            config.remove_section(section)
        else:
            config.remove_option(section,key)

        with open(self.__svn_conf_path+'/'+file,'w') as f:
            config.write(f)
        return True

    # 获取平台信息
    def __get_platform(self):
        os_type_text = ''
        import platform
        systype = platform.system()
        if systype == "Windows":
            os_type_text = 'Windows'
        elif systype == "Linux":
            # os = platform.linux_distribution()
            # os_type = os[0]
            # os_ver = os[1]
            # if 'CentOS' in os_type:
            #     if int(os_ver.split('.')[0]) == 8:
            #         os_type_text = 'CentOS8'
            #     else:
            #         os_type_text = 'CentOS'
            # elif 'Ubuntu' in os_type:
            #     os_type_text = 'Ubuntu'
            # else:
            #     os_type_text = 'Linux'
            aptInstalled = public.ExecShell('command -v apt')
            if aptInstalled[0] != '':
                os_type_text = 'Ubuntu'

            yumInstalled = public.ExecShell('command -v yum')
            if yumInstalled[0] != '':
                os_type_text = 'CentOS'
            
            if os_type_text == '':
                os_type_text = 'Linux'
        else:
            os_type_text = 'Other'

        return os_type_text

    # 【命令行】 - 插件安装
    def install(self):
        import sys
        if sys.version_info[0] == 3 and sys.version_info[1] >= 5:
            public.ExecShell('pip install distro')

        import os.path
        if not os.path.isfile(self.__svn_conf_path):
            public.ExecShell('mkdir -p %s' % (self.__svn_conf_path))

        if not os.path.isfile(self.__svn_conf_path+'/authz') or os.path.getsize(self.__svn_conf_path+'/authz') == 0:
            authz = '''
[aliases]
[groups]
[/]
root=rw
'''
            public.ExecShell('echo "%s" > %s' % (authz,self.__svn_conf_path+'/authz'))

        if not os.path.isfile(self.__svn_conf_path+'/passwd') or os.path.getsize(self.__svn_conf_path+'/passwd') == 0:
            passwd = '''
[users]
root=%s
''' % (public.GetRandomString(16))
            public.ExecShell('echo "%s" > %s' % (passwd,self.__svn_conf_path+'/passwd'))

        if not os.path.isfile(self.__svn_repository_path):
            public.ExecShell('mkdir -p %s' % (self.__svn_repository_path))


        process_info = public.ExecShell('ps auxf|grep -v "grep"|grep svnserve')
        if process_info[0] == '' or os.path.exists('/usr/bin/svnserve') == False:
            # print('安装SVN')
            platform = self.__get_platform()
            if platform == 'CentOS':
                public.ExecShell('yum install subversion -y')
                print(public.ExecShell('sed -i "s/\/var\/svn/\/www\/svn\/repository/g" /etc/sysconfig/svnserve'))
                subversion_config='''
[groups]
[global]
store-plaintext-passwords = yes
    '''
                public.ExecShell('echo "%s" > /etc/subversion/servers' % (subversion_config))
            elif platform == 'Ubuntu':
                public.ExecShell('apt install subversion -y')
                # /etc/subversion/servers
                public.ExecShell('sed -i "s/# store-plaintext-passwords = no/store-plaintext-passwords = yes/g" /etc/subversion/servers')
                service_shell='''
[Unit]
Description=Subversion protocol daemon
After=syslog.target network.target

[Service]
Type=forking
ExecStart=/usr/bin/svnserve --daemon --pid-file=/run/svnserve.pid -r /www/svn/repository

[Install]
WantedBy=multi-user.target
    '''
                public.ExecShell('echo "%s" > /lib/systemd/system/svnserve.service' % (service_shell))
                public.ExecShell('systemctl daemon-reload')

        # 启动程序
        public.ExecShell('systemctl enable svnserve.service')
        public.ExecShell('systemctl start svnserve.service')

        # 开放防火墙端口
        import firewalls
        firewallObject = firewalls.firewalls()
        from public import dict_obj
        get = dict_obj();
        get.port = self.__svn_port
        get.ps = self.__svn_port_info
        firewallObject.AddAcceptPort(get)

        print('install')

    # 【命令行】 - 插件卸载
    def uninstall(self):

        repo_list_src = os.listdir(self.__svn_repository_path)
        for repo in repo_list_src:
            repo_path = self.__svn_repository_path+'/'+repo
            # 清理部署目录
            project_data_file = repo_path+'/conf/config.json'
            project_config = public.ReadFile(project_data_file)
            project_config = json.loads(project_config)
            public.ExecShell('rm -rf %s/.svn' % (project_config['project_path']))

        public.ExecShell('rm -rf %s' % (self.__svn_conf_path))
        public.ExecShell('rm -rf %s' % (self.__svn_repository_path))

        public.ExecShell('systemctl stop svnserve.service')
        public.ExecShell('systemctl disable svnserve.service')

        print('uninstall')

#在命令行模式下执行
if __name__ == "__main__":

    g = svn_deploy_main();
    type = sys.argv[1];

    if type == 'install':
        g.install()
        exit()
    elif type == 'uninstall':
        g.uninstall()
        exit()
