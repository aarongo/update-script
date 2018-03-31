#!/usr/bin/env python
# _*_coding:utf-8_*_
# Author: "Edward.Liu"
# Author-Email: liuyulong@co-mall.com


"""
解决部署时处理软连接
原因：在部署项目的时候有可能存在要挂载静态资源 所以一次性都推过去会冲掉原有的软连接 影响线上使用
改进：
1. 部署推送的时候改为按项目推送 避免一次部署推送所有冲掉软连接
2. 增加部署速度提高准确率
更改后：
在目录结构层增加项目名称一层目录 更改推送配置文件为根据输入的部署项目进行推送相应的目录
"""


import argparse
import logging
import logging.config
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from subprocess import Popen, PIPE


# code 存放位置
CODE_WORKSPACE = "/software/git_code_registroy/core"
# 代码 export 目录
CODE_EXPORT = "/software/git_code_export"
# 代码 export 名称
CODE_EXPORT_NAME = "ejl_test"
# export 路径
export_path = "%s/%s" % (CODE_EXPORT, CODE_EXPORT_NAME)
# 编译后代码存放路径及推送目录
PROJECT_REPOSITORY = "/software/project_repository"


# 部署记录日志
def recordlog():
    loger_path = "/software/script/logger.conf"
    logging.config.fileConfig(loger_path)
    logger = logging.getLogger("ejl")
    return logger


'''
记录部署成功日志
回退部署时调用此日志进行回退
'''


def rollbacklog():
    loger_path = "/software/script/logger.conf"
    logging.config.fileConfig(loger_path)
    logger = logging.getLogger("success")
    return logger


# 切换代码分之
def swith_branch(branch_name):
    # 删除除 master 外的所有的本地分之---明天做细化
    os.chdir(CODE_WORKSPACE)
    check_branch = "git branch | wc -l"
    if check_branch != "1":
        Delete_branch = """git checkout master && git branch | grep -v "master" | xargs git branch -D"""
        delete_code = subprocess.call(Delete_branch, shell=True)
        if delete_code == 0:
            messages = "delete branch success"
            recordlog().info(messages)
    # git 直接切换分之
    swith_command = "/usr/bin/git checkout --track origin/%s" % branch_name
    branch_swith = Popen(swith_command, shell=True, stdout=PIPE, stderr=PIPE)
    while True:
        # 编译显示信息
        update_info = "\033[32mRuncheckout-->Time:\033[0m" + \
                      datetime.now().strftime('%H:%M:%S')
        # 获取编译输出
        newline = branch_swith.stdout.readline()
        # 如果没有输出就退出
        if newline == '' and branch_swith.poll() is not None:
            break
        # 打印编译信息
        sys.stdout.write('%s\r' % update_info)
        # 刷新打印缓存
        sys.stdout.flush()
    stdout, stderr = branch_swith.communicate()
    if branch_swith.returncode == 0:
        print "\033[32mCheckout ejl_test branch: %s Is successful\033[0m" % branch_name
        messages = "update code success"
        recordlog().info(messages)
    else:
        print "\033[32mCheckout ejl_test branch: %s Is Failed\033[0m"
        print stderr
        sys.exit(1)


# git Update
def codeupdate():
    print "\33[32m等待更新项目\033[0m"
    try:
        os.chdir(CODE_WORKSPACE)
        SVN_UPDATE_COMMAND = "/usr/bin/git pull"
        code_update = Popen(SVN_UPDATE_COMMAND, shell=True,
                            stdout=PIPE, stderr=PIPE)
        while True:
            # 编译显示信息
            update_info = "\033[32mRunupdate-->Time:\033[0m" + \
                datetime.now().strftime('%H:%M:%S')
            # 获取编译输出
            newline = code_update.stdout.readline()
            # 如果没有输出就退出
            if newline == '' and code_update.poll() is not None:
                break
            # 打印编译信息
            sys.stdout.write('%s\r' % update_info)
            # 刷新打印缓存
            sys.stdout.flush()
        stdout, stderr = code_update.communicate()
        if (code_update.returncode == 0):
            print "\033[32mUpdate ejl_test Is successful\033[0m"
            messages = "update code success"
            recordlog().info(messages)
        else:
            print "\033[32mUpdate ejl_test Is Failed\033[0m"
            print stderr
            sys.exit(1)
    except KeyboardInterrupt:
        print "\033[31m退出更新\033[0m"


# get git last number
def get_version():
    command = """git log --pretty=format:"%h" -1"""
    os.chdir(CODE_WORKSPACE)
    ret_code = subprocess.Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    if ret_code == 0:
        messages = "get git version success"
        recordlog().info(messages)
    stdout, stderr = ret_code.communicate()
    return stdout


# svn export
def codeexport(branch_name):
    print "\033[32m等待检出目录........\033[0m"
    if os.path.exists(export_path):
        shutil.rmtree(export_path)
    if not os.path.exists(export_path):
        os.makedirs(export_path)
    # 检出 SVN 工作目录
    export_command = "/usr/bin/git archive %s | tar -x -C %s" % (
        branch_name, export_path)
    FNULL = open(os.devnull, 'w')
    # 更换工作目录
    os.chdir(CODE_WORKSPACE)
    ret_code = subprocess.call(
        export_command, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
    if ret_code == 0:
        messages = "code export success"
        recordlog().info(messages)
    return ret_code


# 处理 front gulp 编译问题
def gulp_handle():
    source_dir_name = "/software/node_modules"
    dest_dir_name = "%s/cybershop-front/src/main/websrc/node_modules" % export_path
    shutil.copytree(source_dir_name, dest_dir_name)
    if os.path.isdir(dest_dir_name):
        return "OK"
    else:
        print "handle project front is Failed"
        return "Failed"


# 代码编译
def codebuild(branch_name):
    try:
        if codeexport(branch_name=branch_name) == 0:
            time1 = datetime.now().strftime('%H:%M:%S')
            # 编译命令
            CODE_BUILD_COMMAND = "mvn clean install -Ptest -Dmaven.test.skip=true"
            # 更换工作目录
            os.chdir(export_path)
            # 运行编译命令
            build_status = Popen(CODE_BUILD_COMMAND,
                                 shell=True, stdout=PIPE, stderr=PIPE)
            # 显示编译进度---使用时间作为记录标识
            while True:
                # 编译显示信息
                build_info = "\033[32mRunBuilding-->Time:\033[0m" + \
                    datetime.now().strftime('%H:%M:%S')
                # 获取编译输出
                nextline = build_status.stdout.readline()
                # 如果没有输出就退出
                if nextline == '' and build_status.poll() is not None:
                    break
                # 显示部署进度
                # sys.stdout.write('%s\r' % build_info)
                # 打印编译信息
                sys.stdout.write(nextline)
                # 刷新打印缓存
                sys.stdout.flush()
            stdout, stderr = build_status.communicate()

            time2 = datetime.now().strftime('%H:%M:%S')
            # 计算时间差
            FMT = '%H:%M:%S'
            time_diff = datetime.strptime(
                time2, FMT) - datetime.strptime(time1, FMT)
            if build_status.returncode == 0:
                print "\033[33m编译用时:\033[0m" + "%s" % time_diff
                print "\033[32mBuild ejl_test Is successful\033[0m"
                messages = "build code success"
                recordlog().info(messages)
            else:
                print "\033[32mBuild ejl_test Is Failed\033[0m"
                messages = "build code Failed"
                recordlog().info(messages)
                print stderr
            return build_status.returncode
    except KeyboardInterrupt:
        print "\033[32m 退出编译\033[0m"


def project_name_handle(project_name):
    p_name = ""
    if project_name == "restapi" or project_name == "wxshop":
        p_name = "mobile"
    elif project_name == "erpdocke":
        p_name = "api"
    else:
        p_name = project_name
    return p_name

# 文件处理


def codewar(version, project_name, code_time):
    if codebuild(branch_name=version) == 0:
        print "\033[32m项目包(%s)处理.请等待...........\033[0m" % project_name
        # 项目名称
        CODE_WAR_NAME = "cybershop-%s-0.0.1-SNAPSHOT" % project_name_handle(
            project_name)
        PROJECT_PATH = "%s/%s/%s/%s/%s" % (PROJECT_REPOSITORY,
                                           project_name, code_time, version, CODE_WAR_NAME)
        if not os.path.exists(PROJECT_PATH):
            os.makedirs(PROJECT_PATH)
        # 项目包生成路径
        PROJECT_WAR_PATH = "%s/cybershop-%s/target/%s" % (
            export_path, project_name_handle(project_name), CODE_WAR_NAME) + ".war"
        # 直接将项目包解压到项目目录
        try:
            zip_ref = zipfile.ZipFile(PROJECT_WAR_PATH, 'r')
            zip_ref.extractall(PROJECT_PATH)
            zip_ref.close()
            messages = "project handle success %s" % CODE_WAR_NAME
            recordlog().info(messages)
            print "\033[32m项目包(%s)处理完成!!!\033[0m" % project_name
        except IOError:
            print "\033[31m%s Is Not Exists Please Run bulid\033[0m" % PROJECT_WAR_PATH
    else:
        sys.exit(1)


# 推送项目文件
def pushproject(project_name):
    print "\033[32m等待项目文件推送......\033[0m"
    # 使用ansible rsync模块直接推送到远端
    push_project_directory = "%s/%s" % (PROJECT_REPOSITORY, project_name)
    push_command = """ansible-playbook /etc/ansible/roles/push.yml --extra-vars "hosts=%s src_dir=%s dest_dir=%s" """ % (
        project_name, push_project_directory, PROJECT_REPOSITORY)
    print push_command
    code_push = Popen(push_command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = code_push.communicate()
    messages = "project push to remote Server success "
    recordlog().info(messages)
    print stdout


# 部署项目
def deployproject(project_name, code_time, git_number, tags_name):
    print "\033[32m项目正在部署重启.....\033[0m"
    # ansible 处理软连接、重启项目、检测（脚本输出）项目状态
    ansible_path = "ansible-playbook"
    repository_path = "%s/%s" % (PROJECT_REPOSITORY, project_name)
    other_vars = "hosts=%s project_name=%s repository=%s time=%s git_number=%s" % (
        project_name, project_name_handle(project_name), repository_path, code_time, git_number)
    playbook_path = "/etc/ansible/roles/ejl_deploy.yml"
    deploy_command = """%s %s --tags %s --extra-vars "%s" """ % (
        ansible_path, playbook_path, tags_name, other_vars)
    print deploy_command
    code_deploy = Popen(deploy_command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = code_deploy.communicate()
    print stdout
    if code_deploy.returncode == 0:
        messages = "project deploy successful "
        recordlog().info(messages)
        messages_success = "%s#%s#%s" % (code_time, git_number, project_name)
        rollbacklog().info(messages_success)


# 检测以部署的项目
def checkdeploy():
    path = "/software/script/success.log"
    file_object = open(path, 'rU')
    list_tmp = {}
    try:
        for line in file_object:
            number = (line.split(':')[-1]).split('#')[1]
            d_time = (line.split(':')[-1]).split('#')[0]
            p_name = (line.split(':')[-1]).split('#')[2].strip('\n')
            list_tmp[number] = {"d_time": d_time, "p_name": p_name}
    finally:
        file_object.close()
    return list_tmp


# 回退部署
'''
根据项目已部署记录进行回退
'''


def rollbackdeploy(git_number, project_name, tags_name):
    for number in checkdeploy():
        pro_name = checkdeploy()[number]['p_name']
        if number == git_number and project_name == pro_name:
            code_time = checkdeploy()[number]['d_time']
            ansible_path = "ansible-playbook"
            repository_path = "%s/%s" % (PROJECT_REPOSITORY, project_name)
            other_vars = "hosts=%s project_name=%s repository=%s time=%s git_number=%s" % (
                project_name, project_name, repository_path, code_time, git_number)
            playbook_path = "/etc/ansible/roles/ejl.yml"
            rollback_command = """%s %s --tags %s --extra-vars "%s" """ % (
                ansible_path, playbook_path, tags_name, other_vars)
            rollback_code = Popen(
                rollback_command, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = rollback_code.communicate()
            print stdout
            if rollback_code.returncode == 0:
                messages = "project rollback successful git_number is %s" % git_number
                recordlog().info(messages)


def check_arg(args=None):
    parser = argparse.ArgumentParser(
        description="EG: '%(prog)s'  deploy or rollback glwc ht online")
    parser.add_argument(
        '-n', '--number', help='input git number allow is none')
    parser.add_argument('-b', '--branch', help='input git branch')
    parser.add_argument('-p', '--project', choices=[
                        'web', 'restapi', 'wxshop', 'erpdocke'], help='input project name')
    parser.add_argument('-o', '--operate', choices=['rollback', 'deploy'])
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s 1.0')
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    return parser.parse_args(args)


def main():
    args = check_arg(sys.argv[1:])
    if args.number is None:
        number = get_version()
    else:
        number = args.number
    # 时间  年-月-日
    CODE_TIME = datetime.now().strftime("%Y-%m-%d")
    if args.operate == 'rollback':
        rollbackdeploy(git_number=number,
                       project_name=args.project, tags_name=args.operate)
    if args.operate == 'deploy':
        messages = "deploy git number:%s-deploy project:%s" % (
            number, args.project)
        recordlog().info(messages)
        swith_branch(branch_name=args.branch)
        codeupdate()
        codewar(version=number, project_name=args.project, code_time=CODE_TIME)
        pushproject(project_name=args.project)
        deployproject(project_name=args.project, code_time=CODE_TIME,
                      git_number=number, tags_name=args.operate)


if __name__ == '__main__':
    main()
