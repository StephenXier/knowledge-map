#!/usr/bin/env python
# coding=utf-8
'''
该脚本在pre-receive或post-receive钩子中被调用,也可以直接将该文件作为git的钩子使用
若钩子为shell脚本，则需要加入以下代码调用该脚本:
while read line;do
        echo $line | python $PATH/pre-receive.py
done
当用户执行git push的时候会在远程版本库上触发此脚本
该脚本的主要作用：获取用户提交至版本库的文件列表,提交者及时间信息
'''

import sys, subprocess
import re
import os

__author__ = "zhanghuiwen"
excludPath ="/opt/gitlab/embedded/service/gitlab-shell/custom_hooks/excludes/excludes.txt";
baseGitUrl="http://172.26.0.80:8081"


class Trigger(object):


    def __init__(self):
        '''
        初始化文件列表信息，提交者信息，提交时间,当前操作的分支
        '''
        self.pushAuthor = ""
        self.pushTime = ""
        self.fileList = []
        self.ref = ""



    def __getGitInfo(self):
        '''
        '''
        self.oldObject = sys.argv[2]
        self.newObject = sys.argv[3]
        self.ref = sys.argv[1]

    # 跳过排除的项目
    def _skipExcludeProjects_(self):
        '''
         跳过扫描的项目
        '''
        rev = subprocess.Popen("pwd", shell=True, stdout=subprocess.PIPE);
        gitServerRepoPath = rev.stdout.readline();  # 路径'/var/opt/gitlab/git-data/repositories/alpha/testhook.git'
        paths = gitServerRepoPath.split("repositories");
        projectPath = paths[1];  # /alpha/testhook.git
        rev.stdout.close();

        # 读取配置中的文件
        lines = open(excludPath, "r");
        for line in lines:
            realLine = line.strip("\n");
            result = realLine.replace(baseGitUrl,"")
            if projectPath.strip(" ").strip("\n") == result.strip(" ").strip("\n"):
                lines.close()
                print ("例外项目允许不经过dev和test直接提交")
                exit(0)
            else:
                pass
        lines.close()
        # 继续执行

    def __getPushInfo(self):
        '''
        git show命令获取push作者，时间，以及文件列表
        文件的路径为相对于版本库根目录的一个相对路径
        '''
        rev = subprocess.Popen('git rev-list ' + self.oldObject + '..' + self.newObject, shell=True,
                               stdout=subprocess.PIPE)
        pushList = rev.stdout.readlines()
        pushList = [x.strip() for x in pushList]
        # 循环获取每次提交的文件列表
        for pObject in pushList:
            p = subprocess.Popen('git show ' + pObject, shell=True, stdout=subprocess.PIPE)
            pipe = p.stdout.readlines()
            pipe = [x.strip() for x in pipe]
            self.pushAuthor = pipe[1].strip("Author:").strip()
            self.pushTime = pipe[2].strip("Date:").strip()

            self.fileList.extend(['/'.join(fileName.split("/")[1:]) for fileName in pipe if
                                  fileName.startswith("+++") and not fileName.endswith("null")])

        uBranch = self.ref.split('/')[len(self.ref.split('/')) - 1]
        print '提交分支:  %s' % uBranch
        print '提交变动from:%s to:%s' % (self.oldObject, self.newObject)
        print '提交的commit:%s' % pushList
        # if uBranch == 'dev':
        #    return
        # 循环获取每次提交的文件列表
        for pObject in pushList:
            # 判断是否是merge commit，如果是merge commit则忽略
            gitCatFileCmd = ('git cat-file -p %s') % (pObject)
            p = subprocess.Popen(gitCatFileCmd, shell=True, stdout=subprocess.PIPE)
            pipe = p.stdout.readlines()
            pipe = [x.strip() for x in pipe]
            i = 0
            for branch in pipe:
                if branch.startswith('parent '):
                    i += 1
            if i >= 2:
                continue

            # 如果提交的带上的msg是FIX_MERGE_ERROR则可以通行（避免合错分支引起的问题）
            msgLine = pipe[-1]
            print msgLine
            if msgLine == 'FIX_MERGE_ERROR':
                continue
                # if not re.match(r'^(\w+)-(\d+)', msgLine):
                #       print '\033[1;35m %s 提交的信息没有带上jira编号，请确认添加 \033[0m' % pObject
                #       exit(-1)
            listCmd = ('git branch --contains %s') % (pObject)
            p = subprocess.Popen(listCmd, shell=True, stdout=subprocess.PIPE)
            pipe = p.stdout.readlines()
            pipe = [x.strip() for x in pipe]
            print 'commit:%s->所属分支:%s' % (pObject, pipe)
            # 如果是master分支push提交，必须先提交dev、test
            if 'master' == uBranch:
                if 'dev' not in pipe or 'test' not in pipe:
                    print '\033[1;35m 合并到master的分支必须先在dev、test上经过验证合并才能提交,具体错误提交的hash:%s \033[0m' % pObject
                    exit(-1)
            elif 'test' == uBranch:
                if 'dev' not in pipe:
                    print '\033[1;35m 合并到test的分支必须先在dev上经过验证合并才能提交,具体错误提交的hash:%s \033[0m' % pObject
                    exit(-1)
            branchs = set()
            isMaster = True
            for branch in pipe:
                branch = branch.replace('* ', '')
                if 'master' == branch:
                    isMaster = False
                    break
                if 'test' == branch or 'dev' == branch or 'dev-permission' == branch or 'test-permission' == branch:
                    continue
                    # elif uBranch != 'master' and uBranch != 'test' and uBranch != 'dev' and branch != uBranch:
                    # print '\033[1;35m 提交失败！你合并提交的分支来自于多个分支，请确认,你的分支%s，其他分支%s \033[0m' % (uBranch, branch)
                    # exit(-1)
                branchs.add(branch)
            if len(branchs) >= 2 and isMaster:
                print '\033[1;35m 提交失败！你合并提交的分支来自于多个分支，请确认%s \033[0m' % pipe
                exit(-1)

    def getGitPushInfo(self):
        '''
        返回文件列表信息，提交者信息，提交时间
        '''
        self.__getGitInfo()
        self._skipExcludeProjects_()
        self.__getPushInfo()
        print '========================================='
        print "Time:", self.pushTime
        print "Author:", self.pushAuthor
        print "Ref:", self.ref
        print "Files:", self.fileList
        print '========================================='


if __name__ == "__main__":
    t = Trigger()
    t.getGitPushInfo()
