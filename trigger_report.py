import report_shu
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument('-d', default='none')
parser.add_argument('-t', default='none')
args = parser.parse_args()


if args.d != "none":
    if args.t != 'none':
        report_shu.report_job(setDay=args.d, setTime=eval(args.t))
    else:
        print('请添加-t指定上午或者下午')
else:
    if args.t != 'none':
        date = time.strftime('%Y-%m-%d')
        report_shu.report_job(setDay=date, setTime=eval(args.t))
    else:
        print('\t-d 指定时间\n\t-t 指定日期')
#
