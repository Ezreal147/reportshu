import http.cookiejar
import re
import urllib
from urllib import request

import leancloud
import logging

logging.basicConfig(level=logging.INFO)
leancloud.init("UGJMgGt5gReIppxLVT3k4nY8-9Nh9j0Va", master_key="3amN7lHgr95EeteUMiG9BOb1")


class NoRedirHandler(request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    http_error_301 = http_error_302


def login(person, handler):
    logging.info('=' * 20)
    logging.info(person['name'] + ': 登录中')
    # 第一次请求，用户授权，并获取cookies, requests库在get时会对params重新进行urlEncode,导致params小写变大写，授权不成功，redirect_uri不正确
    req_headers = '''Connection: keep-alive\nCache-Control: max-age=0
        Upgrade-Insecure-Requests: 1
        User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36
        Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
        Sec-Fetch-Site: none
        Sec-Fetch-Mode: navigate
        Sec-Fetch-User: ?1
        Sec-Fetch-Dest: document
        Accept-Encoding: gzip, deflate, br
        Accept-Language: zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7'''

    opener = urllib.request.build_opener(handler)
    opener.addheaders = parseHeaders(req_headers).items()
    res = opener.open('https://selfreport.shu.edu.cn')  # 此处进行了2次重定向

    data = {
        'username': person['account'],
        'password': person['pwd'],
        'login_submit': '正在同步...请稍后'
    }
    data = bytes(urllib.parse.urlencode(data), encoding='utf8')  # 手动将data 进行urlencode

    # 第二次请求，post用户账号密码，此处也有两次重定向，两次重定向Method为GET，第一次POST，因此需要禁止redirect
    req_headers = '''Connection: keep-alive
        Content-Length: ''' + str(len(data)) + '''
        Cache-Control: max-age=0
        Upgrade-Insecure-Requests: 1
        Origin: https://newsso.shu.edu.cn
        Content-Type: application/x-www-form-urlencoded
        User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36
        Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
        Sec-Fetch-Site: same-origin
        Sec-Fetch-Mode: navigate
        Sec-Fetch-User: ?1
        Sec-Fetch-Dest: document
        Referer: ''' + res.url + '''
        Accept-Encoding: gzip, deflate, br
        Accept-Language: zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7'''

    opener = urllib.request.build_opener(NoRedirHandler, handler)
    opener.addheaders = parseHeaders(req_headers).items()
    res = opener.open(res.url, data=data)

    # 第三次请求为手动进行的重定向
    req_headers = '''Connection: keep-alive
        Cache-Control: max-age=0
        Upgrade-Insecure-Requests: 1
        User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36
        Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
        Sec-Fetch-Site: same-origin
        Sec-Fetch-Mode: navigate
        Sec-Fetch-User: ?1
        Sec-Fetch-Dest: document
        Referer: ''' + res.url + '''
        Accept-Encoding: gzip, deflate, br
        Accept-Language: zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7'''
    opener = urllib.request.build_opener(handler)
    opener.addheaders = parseHeaders(req_headers).items()
    res = opener.open('https://newsso.shu.edu.cn' + res.headers['location'])  # 登陆成功，已获取到cookies
    if res.geturl() == 'https://selfreport.shu.edu.cn/':
        logging.info(person['name'] + ': 验证成功')
        return True
    else:
        logging.error(person['name'] + ': 验证失败，请检查学号密码')
        return False


def parseHeaders(string):
    headers = {}
    items = re.split('\n *', string)
    for item in items:
        key_values = item.split(': ')
        headers[key_values[0]] = key_values[1]
    return headers


def check_exist(person):
    report_db = leancloud.Object.extend('report')
    query = report_db.query
    query.equal_to('account', person['account'])
    query_res = query.count()
    if query_res > 0:
        return True
    return False


def save_person(person):
    report = leancloud.Object.extend('report')
    data = report()
    data.set('account', person['account'])
    data.set('pwd', person['pwd'])
    data.set('name', person['name'])
    data.save()


if __name__ == '__main__':
    person = {}
    while True:
        person['account'] = input('·请输入学号>>>')
        person['pwd'] = input('·请输入密码>>>')
        person['name'] = input('·请输入姓名>>>')
        print('*' * 20)
        print('当前输入账号为：\r\n\t学号: {account}\r\n\t密码: {pwd}\r\n\t姓名: {name}'.format(account=person['account'],
                                                                                  pwd=person['pwd'],
                                                                                  name=person['name']))
        confirm = input('·确认添加？(Y/N)>>>').lower()
        if confirm == 'y':
            break
    print('*' * 20)
    logging.info('验证账号密码中...')

    if check_exist(person):
        logging.info('当前账号: {account} 已存在！'.format(account=person['account']))
    else:
        cookie = http.cookiejar.CookieJar()
        handler = urllib.request.HTTPCookieProcessor(cookie)
        if login(person, handler):
            save_person(person)
            logging.info('添加成功')
    # report = leancloud.Object.extend('report')
    # items = report.query.find()
    # persons = []
    # for item in items:
    #     persons.append({
    #         'account': item.get('account'),
    #         'pwd': item.get('pwd'),
    #         'name': item.get('name')
    #     })
    # print(persons)
