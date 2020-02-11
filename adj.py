import pandas as pd
import requests
from finance_util import cum_mul, read_xml
from krxpricereader import krxpricereader as prc
from dateutil.relativedelta import relativedelta


def get_adj_price(short_code, fromdate, todate):
    total = pd.read_pickle('../Database/seibro_code.pickle')
    cust_no = total[total['shotn_isin'] == short_code[1:]]['issuco_custno'].iloc[0]
    codeName = total[total['shotn_isin'] == short_code[1:]]['kor_secn_nm'].iloc[0]
    url = 'http://www.seibro.or.kr/websquare/engine/proworks/callServletService.jsp'

    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/79.0.3945.130 Safari/537.36',
        'Accept': 'application/xml',
        'Referer': 'http://www.seibro.or.kr/websquare/control.jsp?w2xPath=/IPORTAL/user/company/BIP_CNTS01021V.xml'
    }

    schd_payload = '<?xml version="1.0" encoding="UTF-8" ?><reqParam action="termByImptSkedulList" ' \
                   'task="ksd.safe.bip.cnts.Company.process.EntrSkedulPTask"><MENU_NO value="274"/><CMM_BTN_ABBR_NM ' \
                   'value="allview,allview,print,hwp,word,pdf,searchIcon,seach,xls,link,link,wide,wide,top,' \
                   '"/><W2XPATH value="/IPORTAL/user/company/BIP_CNTS01021V.xml"/><ISSUCO_CUSTNO value="' \
                   '{0}"/><DT_TPCD value=""/><FROMDATE value="{1}"/><TODATE value="{2}"/><LIST_TPCD ' \
                   'value=""/><RGT_RACD value=""/></reqParam>'\
        .format(cust_no, fromdate, todate)
    pricer = prc()
    com = pricer.get_stock_price(short_code, fromdate, todate)
    r2 = requests.post(url, data=schd_payload, headers=header).text
    schedule = read_xml(r2)

    fromdate_dt = pd.to_datetime(fromdate)
    todate_dt = pd.to_datetime(todate)
    bef_two_year = todate_dt - relativedelta(years=2)

    div_info_list = []
    while True:
        if bef_two_year > fromdate_dt:
            fromdate_str = bef_two_year.strftime('%Y%m%d')
            todate_str = todate_dt.strftime('%Y%m%d')
            div_payload = '<?xml version="1.0" encoding="UTF-8" ?><reqParam action="divStatInfoPList" ' \
                          'task="ksd.safe.bip.cnts.Company.process.EntrFnafInfoPTask"><RGT_STD_DT_FROM value="' \
                          '{0}"/><RGT_STD_DT_TO value="{1}"/><ISSUCO_CUSTNO value="{2}"/><KOR_SECN_NM ' \
                          'value=""/><SECN_KACD value=""/><RGT_RSN_DTAIL_SORT_CD value=""/><LIST_TPCD ' \
                          'value=""/><START_PAGE value="1"/><END_PAGE value="15"/><MENU_NO ' \
                          'value="285"/><CMM_BTN_ABBR_NM value="allview,allview,print,hwp,word,pdf,searchIcon,seach,' \
                          'xls,link,link,wide,wide,top,"/><W2XPATH ' \
                          'value="/IPORTAL/user/company/BIP_CNTS01041V.xml"/></reqParam>'\
                .format(fromdate_str, todate_str, cust_no)
            r1 = requests.post(url, data=div_payload, headers=header).text
            div_info_ty = read_xml(r1)
            div_info_list.append(div_info_ty)
            todate_dt = bef_two_year
            bef_two_year -= relativedelta(years=2)
        else:
            fromdate_str = fromdate_dt.strftime('%Y%m%d')
            todate_str = todate_dt.strftime('%Y%m%d')
            div_payload = '<?xml version="1.0" encoding="UTF-8" ?><reqParam action="divStatInfoPList" ' \
                          'task="ksd.safe.bip.cnts.Company.process.EntrFnafInfoPTask"><RGT_STD_DT_FROM value="' \
                          '{0}"/><RGT_STD_DT_TO value="{1}"/><ISSUCO_CUSTNO value="{2}"/><KOR_SECN_NM ' \
                          'value=""/><SECN_KACD value=""/><RGT_RSN_DTAIL_SORT_CD value=""/><LIST_TPCD ' \
                          'value=""/><START_PAGE value="1"/><END_PAGE value="15"/><MENU_NO ' \
                          'value="285"/><CMM_BTN_ABBR_NM value="allview,allview,print,hwp,word,pdf,searchIcon,seach,' \
                          'xls,link,link,wide,wide,top,"/><W2XPATH ' \
                          'value="/IPORTAL/user/company/BIP_CNTS01041V.xml"/></reqParam>'\
                .format(fromdate_str, todate_str, cust_no)
            r1 = requests.post(url, data=div_payload, headers=header).text
            div_info_ty = read_xml(r1)
            div_info_list.append(div_info_ty)
            break

    div_info = pd.concat(div_info_list)

    schd = schedule[schedule['rgt_ranm'] == '배당/분배'].copy()
    schd = schd[schd['dt_tpnm'] == '권리락일'].copy()
    schd = schd[['issuco_custno', 'rgt_ranm', 'rgt_std_dt', 'dt_expry_dt']].copy()
    div = div_info[div_info['kor_secn_nm'] == codeName][
        ['rgt_std_dt', 'shotn_isin', 'kor_secn_nm', 'cash_aloc_amt']].copy()

    cash_amt = []
    for idx, std_dt in enumerate(schd['rgt_std_dt']):
        cash = div[div['rgt_std_dt'] == std_dt]['cash_aloc_amt'].iloc[0]
        cash_amt.append(cash)
    schd['cash_aloc_amt'] = cash_amt

    schd.index = pd.to_datetime(schd['dt_expry_dt'])
    schd['cash_aloc_amt'] = schd['cash_aloc_amt'].apply(lambda x: int(x))
    schd.index.name = 'date'

    com['div'] = 0
    com_tmp = com.copy()
    for date in schd.index:
        com_tmp['div'].loc[date] = schd['cash_aloc_amt'].loc[date]

    factor = 1 - com_tmp['div'] / (com_tmp['tdd_clsprc'] - com_tmp['div'])

    com_tmp[['mktcap', 'list_shrs']] = com_tmp[['mktcap', 'list_shrs']].applymap(lambda x: int(x.replace(',', '')))

    divider = com_tmp['list_shrs'].iloc[0]
    cls = com_tmp['mktcap'] / divider * 1000000
    cls = cls.apply(lambda x: int(round(x, 0)))

    adj = cls * cum_mul(factor)
    com_tmp['adj_close'] = adj
    return com_tmp