import requests
import pandas as pd
import numpy as np
import json
import re


class dartreader():
    def __init__(self):
        self.search_url = 'https://opendart.fss.or.kr/api/list.json'
        self.key = 'd92ed39418cc0ab591c1f58204951869bf1549db'

    def get_sep_finstats(self, code, year, quarter, sep = True):
        params = dict()
        params['crtfc_key'] = self.key
        params['corp_code'] = code
        params['bgn_de'] = year + '0101'
        params['end_de'] = str(int(year) + 1) + '0101'
        params['pblntf_ty'] = 'A'

        r = requests.get(self.search_url, params=params).text
        search_result = pd.DataFrame(json.loads(r)['list'])

        report_nm = quarter
        if report_nm == '1q':
            for i in range(len(search_result)):
                report = search_result['report_nm'].iloc[i]
                if (report.find('분기') != -1) & (report.find('03') != -1):
                    rcp_no = search_result['rcept_no'].iloc[i]

        elif report_nm == 'half':
            for i in range(len(search_result)):
                report = search_result['report_nm'].iloc[i]
                if (report.find('반기') != -1):
                    rcp_no = search_result['rcept_no'].iloc[i]

        elif report_nm == '3q':
            for i in range(len(search_result)):
                report = search_result['report_nm'].iloc[i]
                if (report.find('분기') != -1) & (report.find('09') != -1):
                    rcp_no = search_result['rcept_no'].iloc[i]

        elif report_nm == 'year':
            for i in range(len(search_result)):
                report = search_result['report_nm'].iloc[i]
                if (report.find('사업') != -1):
                    rcp_no = search_result['rcept_no'].iloc[i]

        r2 = requests.get('http://dart.fss.or.kr/dsaf001/main.do?rcpNo={}'.format(rcp_no)).text
        pat = re.compile('(?<=viewDoc\().*(?=\))')
        dcp_no = pat.search(r2).group(0).replace("'", "").split(',')[1].strip()

        if sep :
            r3 = requests.get(
                'http://dart.fss.or.kr/report/viewer.do?rcpNo={0}&dcmNo={1}&eleId=15&offset=1332659&length=90711&dtd=dart3.xsd'.format(
                    rcp_no, dcp_no)).text

        else :
            r3 = requests.get(
                'http://dart.fss.or.kr/report/viewer.do?rcpNo={0}&dcmNo={1}&eleId=13&offset=625579&length=120141&dtd=dart3.xsd'.format(
                    rcp_no, dcp_no)).text

        raw = pd.read_html(r3)

        fr_list = []
        for table in raw:
            if len(table) > 10:
                fr_list.append(table)

        print('얻은 재무제표 숫자 : {}개'.format(len(fr_list)))
        return fr_list
