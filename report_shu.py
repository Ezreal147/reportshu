# coding:utf-8

import gzip
import random
from io import BytesIO
from urllib import request
import base64
import time
import http.cookiejar
import urllib.request
import re
import traceback

import leancloud
from bs4 import BeautifulSoup
from apscheduler.schedulers.blocking import BlockingScheduler
import logging

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.getLogger('apscheduler.executors.default').propagate = False
leancloud.init("UGJMgGt5gReIppxLVT3k4nY8-9Nh9j0Va", master_key="3amN7lHgr95EeteUMiG9BOb1")
g_setDay = 0
g_setTime = 0


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
    print(res.geturl())
    if res.geturl() == 'https://selfreport.shu.edu.cn/':
        logging.info(person['name'] + ': 登录成功')
        return True
    else:
        logging.error(person['name'] + ': 登录失败，请检查学号密码')
        return False


def report(person, handler):
    global g_setDay, g_setTime
    opener = urllib.request.build_opener(handler)
    req_headers = '''Connection: keep-alive
    Upgrade-Insecure-Requests: 1
    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36
    Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
    Sec-Fetch-Site: same-origin
    Sec-Fetch-Mode: navigate
    Sec-Fetch-User: ?1
    Sec-Fetch-Dest: document
    Referer: https://selfreport.shu.edu.cn/XueSFX/FanXRB.aspx
    Accept-Encoding: gzip, deflate, br
    Accept-Language: zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7'''
    opener.addheaders = parseHeaders(req_headers).items()
    response = opener.open('https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?t=1')
    body = response.read()
    buff = BytesIO(body)
    f = gzip.GzipFile(fileobj=buff)
    body = f.read().decode('utf-8')
    html = BeautifulSoup(body, 'lxml')
    viewstate_ele = html.select('#__VIEWSTATE')[0]
    view_state = urllib.parse.quote_plus(viewstate_ele.attrs['value'])
    generate = html.select('#__VIEWSTATEGENERATOR')[0]
    generator = generate.attrs['value']
    date = time.strftime('%Y-%m-%d')
    if g_setDay != 0:
        date = g_setDay
    hour = int(time.strftime('%H'))
    if g_setTime != 0:
        if g_setTime == 1:
            hour = 8
        elif g_setTime == 2:
            hour = 18
    if hour > 12:
        title = '每日两报（下午）'
        report_url = f'https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?day={date}&t=2'
    else:
        title = '每日两报（上午）'
        report_url = f'https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?day={date}&t=1'
    tiwen = '36.' + str(random.randint(4, 8))
    fstate = '{"p1_BaoSRQ":{"Text":"' + date + '"},"p1_DangQSTZK":{"F_Items":[["良好","良好",1],["不适","不适",1]],"SelectedValue":"良好"},"p1_ZhengZhuang":{"Hidden":true,"F_Items":[["感冒","感冒",1],["咳嗽","咳嗽",1],["发热","发热",1]],"SelectedValueArray":[]},"p1_TiWen":{"Text":"' + tiwen + '"},"p1_ZaiXiao":{"F_Items":[["不在校","不在校",1],["宝山","宝山校区",1],["延长","延长校区",1],["嘉定","嘉定校区",1],["新闸路","新闸路校区",1]],"SelectedValue":"宝山"},"p1_ddlSheng":{"F_Items":[["-1","选择省份",1,"",""],["北京","北京",1,"",""],["天津","天津",1,"",""],["上海","上海",1,"",""],["重庆","重庆",1,"",""],["河北","河北",1,"",""],["山西","山西",1,"",""],["辽宁","辽宁",1,"",""],["吉林","吉林",1,"",""],["黑龙江","黑龙江",1,"",""],["江苏","江苏",1,"",""],["浙江","浙江",1,"",""],["安徽","安徽",1,"",""],["福建","福建",1,"",""],["江西","江西",1,"",""],["山东","山东",1,"",""],["河南","河南",1,"",""],["湖北","湖北",1,"",""],["湖南","湖南",1,"",""],["广东","广东",1,"",""],["海南","海南",1,"",""],["四川","四川",1,"",""],["贵州","贵州",1,"",""],["云南","云南",1,"",""],["陕西","陕西",1,"",""],["甘肃","甘肃",1,"",""],["青海","青海",1,"",""],["内蒙古","内蒙古",1,"",""],["广西","广西",1,"",""],["西藏","西藏",1,"",""],["宁夏","宁夏",1,"",""],["新疆","新疆",1,"",""],["香港","香港",1,"",""],["澳门","澳门",1,"",""],["台湾","台湾",1,"",""]],"SelectedValueArray":["上海"]},"p1_ddlShi":{"Enabled":true,"F_Items":[["-1","选择市",1,"",""],["上海市","上海市",1,"",""]],"SelectedValueArray":["上海市"]},"p1_ddlXian":{"Enabled":true,"F_Items":[["-1","选择县区",1,"",""],["黄浦区","黄浦区",1,"",""],["卢湾区","卢湾区",1,"",""],["徐汇区","徐汇区",1,"",""],["长宁区","长宁区",1,"",""],["静安区","静安区",1,"",""],["普陀区","普陀区",1,"",""],["虹口区","虹口区",1,"",""],["杨浦区","杨浦区",1,"",""],["宝山区","宝山区",1,"",""],["闵行区","闵行区",1,"",""],["嘉定区","嘉定区",1,"",""],["松江区","松江区",1,"",""],["金山区","金山区",1,"",""],["青浦区","青浦区",1,"",""],["奉贤区","奉贤区",1,"",""],["浦东新区","浦东新区",1,"",""],["崇明区","崇明区",1,"",""]],"SelectedValueArray":["宝山区"]},"p1_FengXDQDL":{"F_Items":[["是","是",1],["否","否",1]],"SelectedValue":"否"},"p1_TongZWDLH":{"F_Items":[["是","是",1],["否","否",1]],"SelectedValue":"否"},"p1_XiangXDZ":{"Text":"上海大学宝山校区"},"p1_QueZHZJC":{"F_Items":[["是","是",1,"",""],["否","否",1,"",""]],"SelectedValueArray":["否"]},"p1_DangRGL":{"SelectedValue":"否","F_Items":[["是","是",1],["否","否",1]]},"p1_GeLSM":{"Hidden":true,"IFrameAttributes":{}},"p1_GeLFS":{"Required":false,"Hidden":true,"F_Items":[["居家隔离","居家隔离",1],["集中隔离","集中隔离",1]],"SelectedValue":null},"p1_GeLDZ":{"Hidden":true},"p1_CengFWH":{"Label":"2020年9月27日后是否在中高风险地区逗留过<span style=\'color:red;\'>（天津东疆港区瞰海轩小区、浦东周浦镇明天华城小区、浦东祝桥镇新生小区、浦东祝桥镇航城七路450弄小区、浦东张江镇顺和路126弄小区、内蒙古满洲里东山街道办事处、内蒙古满洲里北区街道）</span>","F_Items":[["是","是",1],["否","否",1]],"SelectedValue":"否"},"p1_CengFWH_RiQi":{"Hidden":true},"p1_CengFWH_BeiZhu":{"Hidden":true},"p1_JieChu":{"Label":"11月11日至' + time.strftime(
        '%m月%d日') + '是否与来自中高风险地区发热人员密切接触<span style=\'color:red;\'>（天津东疆港区瞰海轩小区、浦东周浦镇明天华城小区、浦东祝桥镇新生小区、浦东祝桥镇航城七路450弄小区、浦东张江镇顺和路126弄小区、内蒙古满洲里东山街道办事处、内蒙古满洲里北区街道）</span>","F_Items":[["是","是",1],["否","否",1]],"SelectedValue":"否"},"p1_JieChu_RiQi":{"Hidden":true},"p1_JieChu_BeiZhu":{"Hidden":true},"p1_TuJWH":{"Label":"11月11日至' + time.strftime(
        '%m月%d日') + '是否乘坐公共交通途径中高风险地区<span style=\'color:red;\'>（天津东疆港区瞰海轩小区、浦东周浦镇明天华城小区、浦东祝桥镇新生小区、浦东祝桥镇航城七路450弄小区、浦东张江镇顺和路126弄小区、内蒙古满洲里东山街道办事处、内蒙古满洲里北区街道）</span>","F_Items":[["是","是",1],["否","否",1]],"SelectedValue":"否"},"p1_TuJWH_RiQi":{"Hidden":true},"p1_TuJWH_BeiZhu":{"Hidden":true},"p1_JiaRen":{"Label":"11月11日至' + time.strftime(
        '%m月%d日') + '家人是否有发热等症状"},"p1_JiaRen_BeiZhu":{"Hidden":true},"p1_SuiSM":{"SelectedValue":"绿色","F_Items":[["红色","红色",1],["黄色","黄色",1],["绿色","绿色",1]]},"p1_LvMa14Days":{"SelectedValue":"是","F_Items":[["是","是",1],["否","否",1]]},"p1":{"Title":"' + title + '","IFrameAttributes":{}}}'
    fstate = urllib.parse.quote_plus(base64.b64encode(fstate.encode('utf-8')))

    data = f'__EVENTTARGET=p1%24ctl00%24btnSubmit' \
           f'&__EVENTARGUMENT=' \
           f'&__VIEWSTATE={view_state}' \
           f'&__VIEWSTATEGENERATOR={generator}' \
           f'&p1%24ChengNuo=p1_ChengNuo' \
           f'&p1%24BaoSRQ={date}' \
           f'&p1%24DangQSTZK=%E8%89%AF%E5%A5%BD' \
           f'&p1%24TiWen={tiwen}' \
           f'&p1%24ZaiXiao=%E5%AE%9D%E5%B1%B1' \
           f'&p1%24ddlSheng%24Value=%E4%B8%8A%E6%B5%B7' \
           f'&p1%24ddlSheng=%E4%B8%8A%E6%B5%B7' \
           f'&p1%24ddlShi%24Value=%E4%B8%8A%E6%B5%B7%E5%B8%82' \
           f'&p1%24ddlShi=%E4%B8%8A%E6%B5%B7%E5%B8%82' \
           f'&p1%24ddlXian%24Value=%E5%AE%9D%E5%B1%B1%E5%8C%BA' \
           f'&p1%24ddlXian=%E5%AE%9D%E5%B1%B1%E5%8C%BA' \
           f'&p1%24FengXDQDL=%E5%90%A6' \
           f'&p1%24TongZWDLH=%E5%90%A6' \
           f'&p1%24XiangXDZ=%E4%B8%8A%E6%B5%B7%E5%A4%A7%E5%AD%A6%E5%AE%9D%E5%B1%B1%E6%A0%A1%E5%8C%BA' \
           f'&p1%24QueZHZJC%24Value=%E5%90%A6' \
           f'&p1%24QueZHZJC=%E5%90%A6' \
           f'&p1%24DangRGL=%E5%90%A6' \
           f'&p1%24GeLDZ=' \
           f'&p1%24CengFWH=%E5%90%A6' \
           f'&p1%24CengFWH_RiQi=' \
           f'&p1%24CengFWH_BeiZhu=' \
           f'&p1%24JieChu=%E5%90%A6' \
           f'&p1%24JieChu_RiQi=' \
           f'&p1%24JieChu_BeiZhu=' \
           f'&p1%24TuJWH=%E5%90%A6' \
           f'&p1%24TuJWH_RiQi=' \
           f'&p1%24TuJWH_BeiZhu=' \
           f'&p1%24JiaRen_BeiZhu=' \
           f'&p1%24SuiSM=%E7%BB%BF%E8%89%B2' \
           f'&p1%24LvMa14Days=%E6%98%AF' \
           f'&p1%24Address2=' \
           f'&p1_GeLSM_Collapsed=false' \
           f'&p1_Collapsed=false' \
           f'&F_STATE={fstate}' \
           f'&F_TARGET=p1_ctl00_btnSubmit'
    req_headers = '''Connection: keep-alive
    Content-Length: {length}
    Accept: text/plain, */*; q=0.01
    X-Requested-With: XMLHttpRequest
    X-FineUI-Ajax: true
    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    Origin: https://selfreport.shu.edu.cn
    Sec-Fetch-Site: same-origin
    Sec-Fetch-Mode: cors
    Sec-Fetch-Dest: empty
    Referer: https://selfreport.shu.edu.cn/XueSFX/HalfdayReport.aspx?t=1
    Accept-Encoding: gzip, deflate, br
    Accept-Language: zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7'''
    opener.addheaders = parseHeaders(req_headers.format(length=len(data))).items()
    response = opener.open(report_url, data=bytes(data, 'utf-8'))
    body = response.read()
    buff = BytesIO(body)
    f = gzip.GzipFile(fileobj=buff)
    body = f.read().decode('utf-8')
    if '提交成功' in body:
        logging.info(person['name'] + ': 上报成功, 体温: ' + str(tiwen))
    else:
        logging.error(person['name'] + ': 上报失败')
        logging.error(person['name'] + ': ' + body)
    logging.info('=' * 20)


def parseHeaders(string):
    headers = {}
    items = re.split('\n *', string)
    for item in items:
        key_values = item.split(': ')
        headers[key_values[0]] = key_values[1]
    return headers


def time_job():
    logging.info(time.strftime("%Y-%m-%d %H:%M:%S"))


def report_job(setDay=0, setTime=0):
    # TODO 获取账号列表
    global g_setDay, g_setTime
    g_setDay = setDay
    g_setTime = setTime
    report_db = leancloud.Object.extend('report')
    items = report_db.query.find()
    persons = []
    for item in items:
        persons.append({
            'account': item.get('account'),
            'pwd': item.get('pwd'),
            'name': item.get('name')
        })
    account = 0
    for person in persons:
        cookie = http.cookiejar.CookieJar()
        handler = urllib.request.HTTPCookieProcessor(cookie)
        account += 1
        if account == 6:
            logging.warning('=' * 17)
            logging.warning('暂停60秒')
            logging.warning('=' * 17)
            time.sleep(60)
            account = 1
        time.sleep(5)
        try:
            if login(person, handler):
                report(person, handler)
        except IOError as e:
            logging.error(person['name'] + ': 发生未知错误')
            traceback.print_exc()


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(report_job, 'cron', hour='7,20', minute=5)

    scheduler.add_job(time_job, 'cron', minute='30')
    scheduler.start()
