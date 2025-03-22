# xlbsvn - 增强版SVN版本控制面板插件

## 简介

xlbsvn是一款修改自宝塔官方的增强版SVN版本控制面板插件，为用户提供了更丰富的协同开发、代码版本管理和自动部署功能。该插件完全免费使用，支持多用户访问控制和权限管理，为团队协作提供便捷高效的解决方案。

## 主要功能

![插件界面预览](static/p1.png)

### 1. 版本库管理
- **创建版本库**: 一键创建SVN版本库
- **版本库配置**: 灵活配置版本库的访问权限
- **用户权限管理**: 详细的用户权限设置，支持读/写/读写多种权限模式
- **匿名访问控制**: 支持设置匿名用户的访问权限
- **版本库删除**: 一键删除不需要的版本库

### 2. 自动部署功能
- **代码自动部署**: 提交代码后自动部署到指定目录
- **自定义部署脚本**: 支持配置部署后执行的自定义脚本，如构建、重启服务等
- **部署日志查看**: 完整记录部署过程，方便问题排查
- **文件权限自动设置**: 自动设置部署文件的用户权限

### 3. 服务管理
- **服务状态监控**: 实时监控SVN服务状态
- **一键启动/停止/重启**: 便捷管理SVN服务

### 4. 便捷操作
- **仓库链接快速复制**: 一键复制SVN仓库地址
- **界面优化**: 友好的用户界面，操作简单直观

## 技术特点

- **安全性**: 支持多种权限控制方式，保障代码安全
- **可靠性**: 自动部署功能包含错误处理和日志记录
- **易用性**: 图形化界面，操作简单
- **兼容性**: 适配主流Linux发行版，支持自动识别系统环境

## 适用场景

- 中小型团队的代码协作开发
- 需要严格版本控制的项目管理
- 自动化部署测试或生产环境
- 代码审核与变更追踪

## 使用说明

1. 在宝塔面板插件商店安装xlbsvn
2. 启动SVN服务
3. 创建版本库并配置用户权限
4. 配置自动部署目录和脚本（可选）
5. 使用SVN客户端连接到服务器

## 开发者信息

- 作者: 小礼拜
- 版本: 1.5
- 项目主页: https://github.com/2955373413/xlbsvn.git

## 注意事项

- 建议在使用前备份重要数据
- 自定义部署脚本具有系统执行权限，请谨慎配置
- 推荐使用最新版宝塔面板以获得最佳体验